$sessionId = "PASTE_YOUR_SESSION_ID_HERE"

# Call `add` tool

Invoke-WebRequest -Uri "http://127.0.0.1:8000/mcp" `
    -Method POST `
    -Headers @{ 
        "Content-Type" = "application/json"; 
        "Accept" = "application/json, text/event-stream"; 
        "Mcp-Session-Id" = $sessionId
    } `
    -Body '{ 
        "jsonrpc": "2.0", 
        "id": 3, 
        "method": "tools/call", 
        "params": { 
            "name": "add", 
            "arguments": { "a": 3, "b": 5 } 
        } 
    }' `
    | Select-Object -ExpandProperty Content


# Call `average` tool

Invoke-WebRequest -Uri "http://127.0.0.1:8000/mcp" `
    -Method POST `
    -Headers @{ 
        "Content-Type" = "application/json"; 
        "Accept" = "application/json, text/event-stream"; 
        "Mcp-Session-Id" = $sessionId
    } `
    -Body '{ 
        "jsonrpc": "2.0", 
        "id": 3, 
        "method": "tools/call", 
        "params": { 
            "name": "average", 
            "arguments": { "numbers": [1,3,5,6] } 
        } 
    }' `
    | Select-Object -ExpandProperty Content
