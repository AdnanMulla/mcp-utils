$sessionId = "PASTE_YOUR_SESSION_ID_HERE"

Invoke-WebRequest -Uri "http://127.0.0.1:8000/mcp" `
    -Method POST `
    -Headers @{ "Content-Type" = "application/json"; "Accept" = "application/json, text/event-stream"; "Mcp-Session-Id" = $sessionId } `
    -Body '{ "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {} }' `
    | Select-Object -ExpandProperty Content