# tests/test_notify.py
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from scripts.notify import send_feishu, send_gmail, notify


def test_send_feishu_posts_to_webhook():
    with patch("scripts.notify.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        send_feishu("https://example.com/webhook", "Test message")
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "Test message" in str(call_args)


def test_notify_uses_feishu_when_configured(tmp_path):
    data_file = tmp_path / "2026-04-13.json"
    data_file.write_text(json.dumps({"ipo_count": 3, "week": "2026-04-13"}))

    env = {
        "FEISHU_WEBHOOK_URL": "https://example.com/feishu",
        "IPO_DATA_FILE": str(data_file),
    }
    with patch.dict(os.environ, env, clear=False), \
         patch("scripts.notify.send_feishu") as mock_feishu, \
         patch("scripts.notify.send_gmail") as mock_gmail:
        notify()

    mock_feishu.assert_called_once()
    mock_gmail.assert_not_called()
    msg = mock_feishu.call_args[0][1]
    assert "3" in msg  # ipo_count


def test_notify_falls_back_to_gmail(tmp_path):
    data_file = tmp_path / "2026-04-13.json"
    data_file.write_text(json.dumps({"ipo_count": 2, "week": "2026-04-13"}))

    env = {
        "FEISHU_WEBHOOK_URL": "",
        "GMAIL_USER": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "secret",
        "IPO_DATA_FILE": str(data_file),
    }
    with patch.dict(os.environ, env, clear=False), \
         patch("scripts.notify.send_feishu") as mock_feishu, \
         patch("scripts.notify.send_gmail") as mock_gmail:
        notify()

    mock_feishu.assert_not_called()
    mock_gmail.assert_called_once()


def test_notify_silent_when_no_config(tmp_path, capsys):
    data_file = tmp_path / "2026-04-13.json"
    data_file.write_text(json.dumps({"ipo_count": 1, "week": "2026-04-13"}))
    env = {
        "FEISHU_WEBHOOK_URL": "", "GMAIL_USER": "", "GMAIL_APP_PASSWORD": "",
        "IPO_DATA_FILE": str(data_file),
    }
    with patch.dict(os.environ, env, clear=False):
        notify()  # Should not raise

    captured = capsys.readouterr()
    assert "配置" in captured.out or "skip" in captured.out.lower()


def test_notify_does_not_crash_on_network_error(tmp_path):
    data_file = tmp_path / "2026-04-13.json"
    data_file.write_text(json.dumps({"ipo_count": 1, "week": "2026-04-13"}))
    env = {
        "FEISHU_WEBHOOK_URL": "https://example.com/feishu",
        "IPO_DATA_FILE": str(data_file),
    }
    with patch.dict(os.environ, env, clear=False), \
         patch("scripts.notify.requests.post", side_effect=Exception("network error")):
        notify()  # Must not raise
