import pytest

from app.uploads import UploadError, safe_display_name, validate_upload

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
JPG = b"\xff\xd8\xff\xe0" + b"0" * 32
GIF = b"GIF89a" + b"0" * 32
WEBP = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"0" * 32
PDF = b"%PDF-1.7\n" + b"0" * 32


@pytest.mark.parametrize(
    "name, mime, data",
    [
        ("a.png", "image/png", PNG),
        ("a.JPG", "image/jpeg", JPG),
        ("a.jpeg", "image/jpeg", JPG),
        ("a.gif", "image/gif", GIF),
        ("a.webp", "image/webp", WEBP),
        ("a.pdf", "application/pdf", PDF),
        ("trace.txt", "text/plain", b"line one\nline two\n"),
        ("server.log", "application/octet-stream", b"ERROR something broke\n"),
    ],
)
def test_good_files_pass(name, mime, data):
    assert validate_upload(name, mime, data) in {
        "image/png", "image/jpeg", "image/gif", "image/webp", "application/pdf", "text/plain",
    }


@pytest.mark.parametrize("name", ["virus.exe", "page.html", "script.js", "noextension", "x.png.exe", ".png"])
def test_bad_extensions_are_rejected(name):
    with pytest.raises(UploadError):
        validate_upload(name, "image/png", PNG)


def test_content_type_must_match_the_extension():
    with pytest.raises(UploadError):
        validate_upload("a.png", "text/html", PNG)


def test_magic_bytes_must_match_the_extension():
    with pytest.raises(UploadError):
        validate_upload("a.png", "image/png", b"<html><script>alert(1)</script></html>")


def test_text_with_null_bytes_is_rejected():
    with pytest.raises(UploadError):
        validate_upload("a.txt", "text/plain", b"hello\x00world")


def test_empty_file_is_rejected():
    with pytest.raises(UploadError):
        validate_upload("a.png", "image/png", b"")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("shot.png", "shot.png"),
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\me\\bug.png", "bug.png"),
        ("we\x00ird\nname.png", "weirdname.png"),
        ("", "file"),
        (None, "file"),
    ],
)
def test_display_names_are_cleaned(raw, expected):
    assert safe_display_name(raw) == expected


def test_display_name_is_length_limited():
    assert len(safe_display_name("a" * 500 + ".png")) <= 255
