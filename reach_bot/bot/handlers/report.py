from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.services.report_service import get_detailed_report, get_report, list_history
from app.services.analysis_service import get_latest_run_for_post
from bot.utils.message_texts import (
    ACCESS_DENIED,
    REPORT_NOT_FOUND,
    REPORT_STILL_RUNNING,
    format_detected_post_line,
    format_report,
)
from domain.enums import UserStatus
from infrastructure.database.connection import AsyncSessionLocal

router = Router()


@router.message(Command("report"))
async def report_handler(message: Message, db_user=None, state: FSMContext = None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(ACCESS_DENIED)
        return

    post_id = None
    run_id = None
    if state:
        data = await state.get_data()
        post_id = data.get("selected_post_id")
        run_id = data.get("last_analysis_run_id")

    if not run_id and not post_id:
        await message.answer(REPORT_NOT_FOUND)
        return

    async with AsyncSessionLocal() as session:
        if not run_id and post_id:
            res = await get_latest_run_for_post(post_id, session)
            if not res["success"]:
                await message.answer(REPORT_NOT_FOUND)
                return
            run = res["data"]
            run_id = run.id

        result = await get_report(run_id, session)

    if not result["success"]:
        await message.answer(REPORT_NOT_FOUND)
        return

    data = result["data"]
    if data["status"] in ("PENDING", "RUNNING"):
        await message.answer(REPORT_STILL_RUNNING)
        return

    finished_at = data["finished_at"] or ""
    if finished_at:
        finished_at = finished_at[:19].replace("T", " ")

    text = format_report(
        post_url=data["post_url"],
        source_views=data["source_views"],
        counted_posts_count=data["counted_posts_count"],
        confirmed_secondary_views=data["confirmed_secondary_views"],
        total_confirmed_reach=data["total_confirmed_reach"],
        skipped_posts_count=data["skipped_posts_count"],
        finished_at=finished_at,
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("details"))
async def details_handler(message: Message, db_user=None, state: FSMContext = None) -> None:
    if db_user is None:
        await message.answer(ACCESS_DENIED)
        return

    if db_user.status == UserStatus.BLOCKED.value:
        await message.answer(ACCESS_DENIED)
        return

    post_id = None
    run_id = None
    if state:
        data = await state.get_data()
        post_id = data.get("selected_post_id")
        run_id = data.get("last_analysis_run_id")

    if not run_id and not post_id:
        await message.answer(REPORT_NOT_FOUND)
        return

    async with AsyncSessionLocal() as session:
        if not run_id and post_id:
            res = await get_latest_run_for_post(post_id, session)
            if not res["success"]:
                await message.answer(REPORT_NOT_FOUND)
                return
            run = res["data"]
            run_id = run.id

        result = await get_detailed_report(run_id, session)

    if not result["success"]:
        await message.answer(REPORT_NOT_FOUND)
        return

    data_report = result["data"]["report"]
    detected = result["data"]["detected_posts"]

    if data_report["status"] in ("PENDING", "RUNNING"):
        await message.answer(REPORT_STILL_RUNNING)
        return

    lines = ["<b>BATAFSIL HISOBOT</b>\n"]
    for dp in detected:
        line = format_detected_post_line(
            status=dp["status"],
            post_url=dp["post_url"] or "",
            views_count=dp["views_count"],
            confirmation_type=dp["confirmation_type"],
            skip_reason=dp["skip_reason"],
        )
        lines.append(line)

    if not detected:
        lines.append("Topilgan postlar yo'q.")

    text = "\n".join(lines)
    # Telegram message limit is 4096 chars
    if len(text) > 4000:
        text = text[:4000] + "\n...(qisqartirildi)"

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("view_report:"))
async def view_report_callback(callback: CallbackQuery, db_user=None, state: FSMContext = None) -> None:
    if db_user is None:
        await callback.answer(ACCESS_DENIED, show_alert=True)
        return

    post_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        res = await get_latest_run_for_post(post_id, session)
        if not res["success"]:
            await callback.answer(REPORT_NOT_FOUND, show_alert=True)
            return

        run = res["data"]
        if run.status in ("PENDING", "RUNNING"):
            await callback.answer(REPORT_STILL_RUNNING, show_alert=True)
            return

        result = await get_report(run.id, session)

    if not result["success"]:
        await callback.answer(REPORT_NOT_FOUND, show_alert=True)
        return

    data = result["data"]
    finished_at = (data["finished_at"] or "")[:19].replace("T", " ")
    text = format_report(
        post_url=data["post_url"],
        source_views=data["source_views"],
        counted_posts_count=data["counted_posts_count"],
        confirmed_secondary_views=data["confirmed_secondary_views"],
        total_confirmed_reach=data["total_confirmed_reach"],
        skipped_posts_count=data["skipped_posts_count"],
        finished_at=finished_at,
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
