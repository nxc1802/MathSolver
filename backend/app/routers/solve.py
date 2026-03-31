from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.dependencies import get_current_user_id
from app.supabase_client import get_supabase
from app.models.schemas import SolveRequest, SolveResponse
from agents.orchestrator import Orchestrator
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["Solve"])
orchestrator = Orchestrator()

@router.post("/{session_id}/solve", response_model=SolveResponse)
async def solve_problem(
    session_id: str, 
    request: SolveRequest, 
    background_tasks: BackgroundTasks,
    user_id=Depends(get_current_user_id)
):
    """
    Gửi câu hỏi giải toán trong một session (Submit geometry problem in a session).
    Lưu câu hỏi vào history và bắt đầu tiến trình giải.
    """
    supabase = get_supabase()
    
    # 1. Kiểm tra quyền sở hữu session
    check = supabase.table("sessions").select("id").eq("id", session_id).eq("user_id", user_id).execute()
    if not check.data:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this session.")

    # 2. Lưu câu hỏi của người dùng vào bảng messages
    supabase.table("messages").insert({
        "session_id": session_id,
        "role": "user",
        "type": "text",
        "content": request.text,
        "metadata": {"image_url": request.image_url} if request.image_url else {}
    }).execute()

    # 3. Tạo Job ID cho tiến trình giải
    job_id = str(uuid.uuid4())
    supabase.table("jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "session_id": session_id,
        "status": "processing",
        "input_text": request.text
    }).execute()

    # 4. Chạy orchestrator ngầm (Background task)
    background_tasks.add_task(process_session_job, job_id, session_id, request, user_id)

    # 5. Cập nhật tiêu đề session dựa trên input đầu tiên (nếu tiêu đề mặc định)
    if check.data:
        # Lấy title hiện tại của session
        title_check = supabase.table("sessions").select("title").eq("id", session_id).execute()
        if title_check.data and title_check.data[0]["title"] == "Bài toán mới":
            new_title = request.text[:50] + ("..." if len(request.text) > 50 else "")
            supabase.table("sessions").update({"title": new_title}).eq("id", session_id).execute()

    return SolveResponse(job_id=job_id, status="processing")

async def process_session_job(job_id: str, session_id: str, request: SolveRequest, user_id: str):
    """
    Tiến trình giải toán ngầm, cập nhật cả bảng jobs và bảng messages (history).
    """
    from app.main import notify_status # Import ngầm để tránh loop
    
    async def status_update(status: str):
        await notify_status(job_id, {"status": status})

    supabase = get_supabase()
    try:
        # Chạy Orchestrator
        result = await orchestrator.run(
            request.text, 
            request.image_url, 
            job_id=job_id, 
            session_id=session_id,
            status_callback=status_update,
            request_video=request.request_video
        )
        
        status = result.get("status", "error") if "error" not in result else "error"
        
        # Cập nhật bảng jobs
        supabase.table("jobs").update({
            "status": status,
            "result": result
        }).eq("id", job_id).execute()

        # Nếu không có video (hoặc video xong ngay - ít khả năng), lưu message ngay
        # Nếu có video, worker sẽ cập nhật job sang success sau.
        if status != "rendering_queued":
            # Lưu câu trả lời của AI vào history
            supabase.table("messages").insert({
                "session_id": session_id,
                "role": "assistant",
                "type": "analysis" if "error" not in result else "error",
                "content": result.get("semantic_analysis", "Đã có lỗi xảy ra.") if "error" not in result else result["error"],
                "metadata": {
                    "job_id": job_id,
                    "coordinates": result.get("coordinates"),
                    "geometry_dsl": result.get("geometry_dsl")
                }
            }).execute()

        await notify_status(job_id, {"status": status, "result": result})
        
    except Exception as e:
        logger.error(f"Error processing session job {job_id}: {str(e)}")
        supabase.table("jobs").update({
            "status": "error",
            "result": {"error": str(e)}
        }).eq("id", job_id).execute()
        
        # Lưu tin nhắn lỗi vào history
        supabase.table("messages").insert({
            "session_id": session_id,
            "role": "assistant",
            "type": "error",
            "content": f"Lỗi hệ thống: {str(e)}",
            "metadata": {"job_id": job_id}
        }).execute()
        
        await notify_status(job_id, {"status": "error", "message": str(e)})
