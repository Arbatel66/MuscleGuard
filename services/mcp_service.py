from mcp.server.fastmcp import FastMCP
from sync_service import get_current_hr
# 1. 初始化 MCP 服务

mcp = FastMCP("MuscleGuard-Pro-Server")

@mcp.tool()
def get_current_heart_rate(session_id: str):
    """
        获取指定用户的实时心率数据。
        当你需要判断用户当前的运动强度时，请调用此工具。
        """
    return get_current_hr(session_id = session_id)


