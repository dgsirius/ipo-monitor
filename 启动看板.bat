@echo off
cd /d "%~dp0"
echo 正在启动 IPO Monitor 本地看板...
echo 浏览器打开后点击绿色「生成完整版」按钮即可运行 AI 分析
echo 按 Ctrl+C 可关闭服务器
echo.
python scripts/local_server.py
pause
