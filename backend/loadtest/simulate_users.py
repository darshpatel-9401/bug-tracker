"""Simulate many users hammering a RUNNING API, then print a report.

Each simulated user registers, logs in, creates a project and a few tickets, comments,
lists and searches tickets, and tries a handful of things it must NOT be allowed to do
(touching another user's project, using a forged token). Any "must be refused" request
that is accepted is counted as a security failure.

    pip install httpx
    python loadtest/simulate_users.py --base-url http://localhost:8000 --users 1000 --concurrency 50

Run it against a throwaway database, never against production.
"""
import argparse
import asyncio
import random
import statistics
import time
import uuid
from collections import Counter

import httpx


class Stats:
    def __init__(self):
        self.latencies = []
        self.status_counts = Counter()
        self.unexpected = []  # (what, status) for responses we did not expect
        self.security_failures = []

    def record(self, label, response, expected):
        self.status_counts[(label, response.status_code)] += 1
        if response.status_code not in expected:
            self.unexpected.append((label, response.status_code))


async def timed(client, stats, label, expected, method, url, **kwargs):
    started = time.perf_counter()
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.HTTPError as error:
        stats.unexpected.append((label, f"network error: {type(error).__name__}"))
        return None
    stats.latencies.append(time.perf_counter() - started)
    stats.record(label, response, expected)
    return response


async def one_user(index, client, stats, shared):
    email = f"sim{index}-{uuid.uuid4().hex[:8]}@example.com"
    password = "Simulated123"

    r = await timed(client, stats, "register", {201}, "POST", "/api/auth/register",
                    json={"email": email, "full_name": f"Sim {index}", "password": password})
    if r is None or r.status_code != 201:
        return
    r = await timed(client, stats, "login", {200}, "POST", "/api/auth/login", json={"email": email, "password": password})
    if r is None or r.status_code != 200:
        return
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = await timed(client, stats, "create_project", {201}, "POST", "/api/projects",
                    json={"name": f"Project {index}"}, headers=headers)
    if r is None or r.status_code != 201:
        return
    project_id = r.json()["id"]
    shared["projects"].append(project_id)

    ticket_ids = []
    for n in range(random.randint(2, 5)):
        r = await timed(client, stats, "create_ticket", {201}, "POST", f"/api/projects/{project_id}/tickets",
                        json={"title": f"Bug {n} from {index}", "type": random.choice(["bug", "task", "feature"]),
                              "priority": random.choice(["low", "medium", "high", "critical"])}, headers=headers)
        if r is not None and r.status_code == 201:
            ticket_ids.append(r.json()["id"])

    for ticket_id in ticket_ids[:2]:
        await timed(client, stats, "comment", {201}, "POST", f"/api/tickets/{ticket_id}/comments",
                    json={"body": "Investigating"}, headers=headers)
        await timed(client, stats, "move_ticket", {200}, "PATCH", f"/api/tickets/{ticket_id}",
                    json={"status": random.choice(["in_progress", "in_review", "done"])}, headers=headers)

    await timed(client, stats, "list_tickets", {200}, "GET", f"/api/projects/{project_id}/tickets", headers=headers)
    await timed(client, stats, "search", {200}, "GET", f"/api/projects/{project_id}/tickets", params={"q": "bug"}, headers=headers)

    # ---- things that MUST be refused ----
    other = [p for p in shared["projects"] if p != project_id]
    if other:
        victim = random.choice(other)
        for label, method, url, body in [
            ("cross_read_project", "GET", f"/api/projects/{victim}", None),
            ("cross_list_tickets", "GET", f"/api/projects/{victim}/tickets", None),
            ("cross_create_ticket", "POST", f"/api/projects/{victim}/tickets", {"title": "intruder"}),
            ("cross_add_self", "POST", f"/api/projects/{victim}/members", {"email": email, "role": "admin"}),
            ("cross_delete_project", "DELETE", f"/api/projects/{victim}", None),
        ]:
            r = await timed(client, stats, label, {403, 404}, method, url, json=body, headers=headers)
            if r is not None and r.status_code < 400:
                stats.security_failures.append((label, r.status_code))

    forged = {"Authorization": "Bearer " + "a" * 20 + "." + "b" * 20 + "." + "c" * 20}
    r = await timed(client, stats, "forged_token", {401}, "GET", "/api/auth/me", headers=forged)
    if r is not None and r.status_code < 400:
        stats.security_failures.append(("forged_token", r.status_code))


async def main(args):
    stats = Stats()
    shared = {"projects": []}
    semaphore = asyncio.Semaphore(args.concurrency)
    limits = httpx.Limits(max_connections=args.concurrency * 2)

    async with httpx.AsyncClient(base_url=args.base_url, timeout=30, limits=limits) as client:
        health = await client.get("/api/health")
        health.raise_for_status()

        async def guarded(i):
            async with semaphore:
                await one_user(i, client, stats, shared)

        started = time.perf_counter()
        await asyncio.gather(*(guarded(i) for i in range(args.users)))
        elapsed = time.perf_counter() - started

    total = len(stats.latencies)
    print(f"\nSimulated users:   {args.users}")
    print(f"Total requests:    {total}")
    print(f"Wall time:         {elapsed:.1f}s  ({total / elapsed:.0f} req/s)")
    if stats.latencies:
        ordered = sorted(stats.latencies)
        p = lambda q: ordered[min(len(ordered) - 1, int(len(ordered) * q))] * 1000
        print(f"Latency ms:        mean {statistics.mean(ordered) * 1000:.0f} | p50 {p(0.5):.0f} | p95 {p(0.95):.0f} | p99 {p(0.99):.0f} | max {ordered[-1] * 1000:.0f}")
    print(f"Unexpected replies: {len(stats.unexpected)}")
    for item, count in Counter(stats.unexpected).most_common(15):
        print(f"   {item}  x{count}")
    print(f"SECURITY FAILURES:  {len(stats.security_failures)}")
    for item, count in Counter(stats.security_failures).most_common(15):
        print(f"   {item}  x{count}")
    print("\nStatus codes by endpoint:")
    for (label, code), count in sorted(stats.status_counts.items()):
        print(f"   {label:22s} {code}  x{count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--users", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=50)
    asyncio.run(main(parser.parse_args()))
