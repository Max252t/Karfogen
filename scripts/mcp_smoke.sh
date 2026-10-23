#!/bin/sh
PORT="${1:-8765}"
URL="http://127.0.0.1:${PORT}/mcp"

call() {
    curl -s -X POST "$URL" -H "Content-Type: application/json" -d "$1"
    echo
}

call '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}'
call '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
call '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"get_machine","arguments":{}}}'
call '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"list_objects","arguments":{}}}'
call '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"no_such_tool","arguments":{}}}'
