import json
import os
import smtplib
from email.mime.text import MIMEText

import requests


def _build_message(ipo_count: int, week: str) -> str:
    return (
        f"📊 IPO Monitor 周报更新\n"
        f"本周新增：{ipo_count} 家公司待 IPO\n"
        f"数据更新周：{week}\n"
        f"👉 运行命令：python scripts/generate.py\n"
        f"预览：https://dgsirius.github.io/ipo-monitor"
    )


def send_feishu(webhook_url: str, message: str) -> None:
    resp = requests.post(
        webhook_url,
        json={"msg_type": "text", "content": {"text": message}},
        timeout=10,
    )
    resp.raise_for_status()


def send_gmail(user: str, app_password: str, message: str) -> None:
    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = "📊 IPO Monitor 周报更新"
    msg["From"] = user
    msg["To"] = user
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, app_password)
        server.sendmail(user, user, msg.as_string())


def notify() -> None:
    data_file = os.environ.get("IPO_DATA_FILE", "")
    feishu_url = os.environ.get("FEISHU_WEBHOOK_URL", "")
    gmail_user = os.environ.get("GMAIL_USER", "")
    gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "")

    ipo_count, week = 0, "unknown"
    if data_file and os.path.exists(data_file):
        with open(data_file, encoding="utf-8") as f:
            d = json.load(f)
        ipo_count = d.get("ipo_count", 0)
        week = d.get("week", "unknown")

    message = _build_message(ipo_count, week)

    try:
        if feishu_url:
            send_feishu(feishu_url, message)
            print(f"[notify] Feishu notification sent ({ipo_count} IPOs)")
        elif gmail_user and gmail_pass:
            send_gmail(gmail_user, gmail_pass, message)
            print(f"[notify] Gmail notification sent to {gmail_user}")
        else:
            print("[notify] 未配置通知方式，跳过")
    except Exception as e:
        print(f"[notify] Warning: notification failed: {e}")


if __name__ == "__main__":
    notify()
