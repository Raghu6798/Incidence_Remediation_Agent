# log_aggregation_tool.py

import requests
from typing import Optional, Type, ClassVar

from pydantic import BaseModel, Field
from langchain_core.callbacks import (
    CallbackManagerForToolRun,
    AsyncCallbackManagerForToolRun,
)
from tools.base import AbstractTool


class LokiQueryInput(BaseModel):
    query: str = Field(..., description="Loki log query in LogQL format")


class LokiLogAggregationTool(AbstractTool):
    name: str = "LokiLogAggregationTool"
    description: str = "Query logs from Grafana Loki using LogQL"
    args_schema: Optional[Type[BaseModel]] = LokiQueryInput
    return_direct: bool = True

    LOKI_API_URL: ClassVar[str] = "http://localhost:3100/loki/api/v1/query"

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            response = requests.get(self.LOKI_API_URL, params={"query": query})
            response.raise_for_status()
            data = response.json()

            logs = []
            for stream in data.get("data", {}).get("result", []):
                for log_entry in stream.get("values", []):
                    timestamp, message = log_entry
                    logs.append(f"{timestamp}: {message}")

            return "\n".join(logs) if logs else "No logs found."
        except Exception as e:
            return f"Error querying Loki: {e}"

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        from asyncio import to_thread

        return await to_thread(self._run, query=query, run_manager=run_manager)


if __name__ == "__main__":
    tool = LokiLogAggregationTool()
    result = tool.invoke({"query": '{job="containerlogs"}'})
    print(result)
