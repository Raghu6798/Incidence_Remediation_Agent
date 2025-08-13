from langchain_core.tools import tool
from pydantic import BaseModel, RootModel, Field
from typing import List, Optional, Dict, Any
import requests
import time
from datetime import datetime

# -------------------- Models --------------------

class Stream(BaseModel):
    filename: str
    job: str

# RootModel for each log entry: [timestamp, log_line]
class ValueEntry(RootModel[List[str]]):
    pass

class ResultEntry(BaseModel):
    stream: Stream
    values: List[ValueEntry]

class SummaryStats(BaseModel):
    bytesProcessedPerSecond: float
    linesProcessedPerSecond: float
    totalBytesProcessed: int
    totalLinesProcessed: int
    execTime: float
    queueTime: float
    subqueries: int
    totalEntriesReturned: int
    splits: int
    shards: int
    totalPostFilterLines: int
    totalStructuredMetadataBytesProcessed: int

class ChunkStats(BaseModel):
    headChunkBytes: int
    headChunkLines: int
    decompressedBytes: int
    decompressedLines: int
    compressedBytes: int
    totalDuplicates: int
    postFilterLines: int
    headChunkStructuredMetadataBytes: int
    decompressedStructuredMetadataBytes: int

class StoreStats(BaseModel):
    totalChunksRef: int
    totalChunksDownloaded: int
    chunksDownloadTime: float
    chunk: ChunkStats

class QuerierStats(BaseModel):
    store: StoreStats

class IngesterStats(BaseModel):
    totalReached: int
    totalChunksMatched: int
    totalBatches: int
    totalLinesSent: int
    store: StoreStats

class CacheChunkIndexResultStats(BaseModel):
    entriesFound: int
    entriesRequested: int
    entriesStored: int
    bytesReceived: int
    bytesSent: int
    requests: int
    downloadTime: float

class CacheStats(BaseModel):
    chunk: CacheChunkIndexResultStats
    index: CacheChunkIndexResultStats
    result: CacheChunkIndexResultStats
    statsResult: CacheChunkIndexResultStats

class Stats(BaseModel):
    summary: SummaryStats
    querier: QuerierStats
    ingester: IngesterStats
    cache: CacheStats

class Data(BaseModel):
    resultType: str
    result: List[ResultEntry]
    stats: Stats

class LokiResponse(BaseModel):
    status: str
    data: Data

# -------------------- Tool Input Schema --------------------

class LogRetrievalInput(BaseModel):
    """Input schema for log retrieval tool."""
    job_name: str = Field(
        description="Name of the job to retrieve logs for (e.g., 'fastapi-app', 'nginx', 'postgres')"
    )
    hours_back: Optional[int] = Field(
        default=1,
        description="Number of hours back from current time to fetch logs (default: 1 hour)"
    )
    limit: Optional[int] = Field(
        default=1000,
        description="Maximum number of log entries to retrieve (default: 1000)"
    )
    loki_url: Optional[str] = Field(
        default="http://localhost:3100",
        description="Base URL of the Loki instance (default: http://localhost:3100)"
    )
    additional_filters: Optional[str] = Field(
        default="",
        description="Additional LogQL filters to apply (e.g., '|= \"error\"' for error logs)"
    )

# -------------------- LangChain Tool --------------------

@tool("retrieve_job_logs", args_schema=LogRetrievalInput)
def retrieve_job_logs(
    job_name: str,
    hours_back: int = 1,
    limit: int = 1000,
    loki_url: str = "http://localhost:3100",
    additional_filters: str = ""
) -> Dict[str, Any]:
    """
    Retrieve logs for a specific job from Loki logging system.
    
    This tool fetches logs from a Loki instance for a given job name within
    a specified time range. It returns structured log data including timestamps,
    log lines, and query statistics.
    
    Args:
        job_name: Name of the job to retrieve logs for
        hours_back: Number of hours back from current time to fetch logs
        limit: Maximum number of log entries to retrieve
        loki_url: Base URL of the Loki instance
        additional_filters: Additional LogQL filters to apply
    
    Returns:
        Dictionary containing:
        - status: Query status
        - log_count: Total number of log entries retrieved
        - logs: List of log entries with timestamps and messages
        - stats: Query execution statistics
        - error: Error message if query failed
    """
    
    try:
        # Construct the query URL
        url = f"{loki_url}/loki/api/v1/query_range"
        
        # Build LogQL query
        base_query = f'{{job="{job_name}"}}'
        if additional_filters:
            query = f"{base_query} {additional_filters}"
        else:
            query = base_query
        
        # Calculate time range (Loki expects nanosecond timestamps)
        current_time = int(time.time())
        start_time = current_time - (hours_back * 3600)  # hours_back hours ago
        
        params = {
            "query": query,
            "start": str(start_time * 1_000_000_000),  # Convert to nanoseconds
            "end": str(current_time * 1_000_000_000),   # Convert to nanoseconds
            "limit": str(limit)
        }
        
        # Make the request
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        # Parse the response
        parsed = LokiResponse(**response.json())
        
        # Extract logs in a more readable format
        logs = []
        total_entries = 0
        
        for result in parsed.data.result:
            stream_info = {
                "filename": result.stream.filename,
                "job": result.stream.job
            }
            
            for entry in result.values:
                timestamp_ns, log_line = entry.model_dump()
                
                # Convert nanosecond timestamp to readable format
                timestamp_sec = int(timestamp_ns) / 1_000_000_000
                readable_timestamp = datetime.fromtimestamp(timestamp_sec).isoformat()
                
                logs.append({
                    "timestamp": readable_timestamp,
                    "timestamp_ns": timestamp_ns,
                    "message": log_line,
                    "stream": stream_info
                })
                total_entries += 1
        
        # Sort logs by timestamp (most recent first)
        logs.sort(key=lambda x: x["timestamp_ns"], reverse=True)
        
        return {
            "status": parsed.status,
            "log_count": total_entries,
            "logs": logs,
            "query": query,
            "time_range": {
                "start": datetime.fromtimestamp(start_time).isoformat(),
                "end": datetime.fromtimestamp(current_time).isoformat(),
                "hours_back": hours_back
            },
            "stats": {
                "total_entries_returned": parsed.data.stats.summary.totalEntriesReturned,
                "execution_time": parsed.data.stats.summary.execTime,
                "bytes_processed": parsed.data.stats.summary.totalBytesProcessed,
                "lines_processed": parsed.data.stats.summary.totalLinesProcessed
            }
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": f"Failed to connect to Loki: {str(e)}",
            "log_count": 0,
            "logs": []
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": f"Unexpected error: {str(e)}",
            "log_count": 0,
            "logs": []
        }

# -------------------- Alternative: Function-based Tool --------------------

def create_log_retrieval_tool(default_loki_url: str = "http://localhost:3100"):
    """
    Factory function to create a log retrieval tool with a specific Loki URL.
    Useful when you have multiple Loki instances or want to configure defaults.
    """
    
    @tool("retrieve_job_logs_configured")
    def retrieve_job_logs_configured(
        job_name: str,
        hours_back: int = 1,
        limit: int = 1000,
        additional_filters: str = ""
    ) -> Dict[str, Any]:
        """Retrieve logs for a specific job with pre-configured Loki URL."""
        return retrieve_job_logs(
            job_name=job_name,
            hours_back=hours_back,
            limit=limit,
            loki_url=default_loki_url,
            additional_filters=additional_filters
        )
    
    return retrieve_job_logs_configured