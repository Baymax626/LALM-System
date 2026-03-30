# Windows 一键启动脚本
# 请以管理员身份运行 PowerShell

Write-Host "Starting LALM System..." -ForegroundColor Green

# 1. 启动 Python 模型服务 (Mock)
Write-Host "1. Starting Python Model Service (Port 8001)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'd:\Suda\毕设 - 副本\web_system\model_service'; pip install fastapi uvicorn numpy; python main.py"

# 等待几秒确保 Python 启动
Start-Sleep -Seconds 3

# 2. 启动 Java 后端
Write-Host "2. Starting Java Backend (Port 8080)..."
# 注意：假设已安装 Maven 且在 PATH 中。如果没有，请手动在 IDEA 中启动。
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'd:\Suda\毕设 - 副本\web_system\model_service\backend_java'; mvn spring-boot:run"

# 3. 启动前端
Write-Host "3. Starting Frontend (Port 5173)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'd:\Suda\毕设 - 副本\web_system\frontend'; npm install; npm run dev"

Write-Host "All services started!"
Write-Host "Please visit: http://localhost:5173"
