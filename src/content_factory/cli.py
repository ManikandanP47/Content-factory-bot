from __future__ import annotations

import traceback
from pathlib import Path
from typing import Optional

import click

from content_factory.audio_mix import mix_audio
from content_factory.config import load_config, output_dir
from content_factory.jobs import (
    load_job,
    load_script,
    new_job_id,
    save_job,
    save_script,
    slugify,
    update_job,
)
from content_factory.models import JobStatus
from content_factory.script_writer import write_script
from content_factory.video_bridge import render_video, write_remotion_props
from content_factory.voice import synthesize_voice


@click.group()
@click.version_option(package_name="content-factory")
def main() -> None:
    """Content Factory — script → voice → video → Drive / YouTube / Instagram."""


@main.command("produce")
@click.option("--topic", required=True, help="Video topic / brief")
@click.option("--config", "config_path", default=None, help="Path to YAML config")
@click.option(
    "--skip-video",
    is_flag=True,
    help="Stop after audio (useful for testing voice)",
)
@click.option("--dry-run", is_flag=True, help="Write script only")
def produce(
    topic: str, config_path: Optional[str], skip_video: bool, dry_run: bool
) -> None:
    """Produce a local short (script + voice + video)."""
    config = load_config(config_path)
    job_id = new_job_id(topic)
    job_dir = output_dir(job_id)
    status = JobStatus(job_id=job_id, topic=topic, stage="script")
    save_job(status)

    click.echo(f"[job] {job_id}")
    click.echo(f"[script] Writing for: {topic}")
    script = write_script(topic, config)
    script_path = save_script(job_id, script)
    update_job(job_id, script_path=str(script_path), stage="script_done")
    click.echo(f"[script] {script.title}")

    if dry_run:
        click.echo("[dry-run] Stopping after script")
        return

    narration = script.full_narration()
    click.echo("[voice] Synthesizing narration…")
    voice_path = synthesize_voice(narration, job_dir / "voice", config)
    update_job(job_id, voice_path=str(voice_path), stage="voice_done")
    click.echo(f"[voice] {voice_path}")

    click.echo("[audio] Mixing / normalizing…")
    mixed = mix_audio(voice_path, job_dir / "mixed", config)
    update_job(job_id, mixed_audio_path=str(mixed), stage="audio_done")
    click.echo(f"[audio] {mixed}")

    if skip_video:
        click.echo("[skip-video] Done")
        return

    click.echo("[video] Building props + render…")
    props_path, props = write_remotion_props(script, mixed, job_dir, config)
    update_job(job_id, props_path=str(props_path), stage="props_done")
    video_path = render_video(props_path, job_dir, props)
    update_job(job_id, video_path=str(video_path), stage="complete")
    click.echo(f"[video] {video_path}")
    click.echo(f"[done] Job {job_id} ready. Publish with:")
    click.echo(f'  content-factory publish --job {job_id} --channels drive,youtube')


@main.command("publish")
@click.option("--job", "job_id", required=True, help="Job id under output/")
@click.option(
    "--channels",
    default="drive",
    help="Comma list: drive,youtube,instagram",
)
@click.option(
    "--privacy",
    type=click.Choice(["private", "unlisted", "public"]),
    default=None,
)
@click.option("--dry-run", is_flag=True)
@click.option("--instagram-video-url", default=None, help="Public HTTPS URL for IG Reels")
def publish(
    job_id: str,
    channels: str,
    privacy: Optional[str],
    dry_run: bool,
    instagram_video_url: Optional[str],
) -> None:
    """Upload a produced job to Drive / YouTube / Instagram."""
    import os

    config = load_config()
    status = load_job(job_id)
    script = load_script(job_id)
    job_dir = output_dir(job_id)
    video_path = Path(status.video_path or job_dir / "final.mp4")
    channel_list = [c.strip().lower() for c in channels.split(",") if c.strip()]

    if dry_run:
        click.echo(f"[dry-run] Would publish {job_id} → {channel_list}")
        return

    if "drive" in channel_list:
        from content_factory.drive_upload import upload_job_to_drive

        click.echo("[drive] Uploading…")
        try:
            result = upload_job_to_drive(
                job_dir, job_id, slugify(script.title), config
            )
            update_job(job_id, drive=result, stage="published_drive")
            click.echo(f"[drive] {result.get('folder_url')}")
        except Exception as exc:
            update_job(job_id, error=str(exc))
            click.echo(f"[drive] FAILED: {exc}")
            traceback.print_exc()

    if "youtube" in channel_list:
        from content_factory.youtube_upload import upload_youtube_short

        priv = privacy or config.get("channels", {}).get(
            "youtube_privacy", "private"
        )
        click.echo(f"[youtube] Uploading as {priv}…")
        try:
            result = upload_youtube_short(
                video_path,
                title=script.title,
                description=script.description,
                tags=script.hashtags,
                privacy=priv,  # type: ignore[arg-type]
                category_id=str(
                    config.get("channels", {}).get("youtube_category_id", "22")
                ),
            )
            update_job(job_id, youtube=result, stage="published_youtube")
            click.echo(f"[youtube] {result.get('url')}")
        except Exception as exc:
            update_job(job_id, error=str(exc))
            click.echo(f"[youtube] FAILED: {exc}")
            traceback.print_exc()

    if "instagram" in channel_list:
        from content_factory.instagram_upload import (
            upload_instagram_reel,
            upload_instagram_reel_from_drive_link,
        )

        caption = (
            f"{script.description}\n\n"
            + " ".join(f"#{t.lstrip('#')}" for t in script.hashtags)
        )
        click.echo("[instagram] Publishing Reel…")
        try:
            if instagram_video_url:
                os.environ["INSTAGRAM_VIDEO_URL"] = instagram_video_url
                result = upload_instagram_reel(
                    video_path,
                    caption=caption,
                    share_to_feed=bool(
                        config.get("channels", {}).get(
                            "instagram_share_to_feed", True
                        )
                    ),
                )
            else:
                drive = load_job(job_id).drive or {}
                files = drive.get("files") or []
                mp4 = next(
                    (f for f in files if f.get("name") == "final.mp4"), None
                )
                if not mp4:
                    raise RuntimeError(
                        "Publish to Drive first (or pass --instagram-video-url)."
                    )
                result = upload_instagram_reel_from_drive_link(
                    mp4["id"], caption=caption
                )
            update_job(job_id, instagram=result, stage="published_instagram")
            click.echo(f"[instagram] media_id={result.get('media_id')}")
        except Exception as exc:
            update_job(job_id, error=str(exc))
            click.echo(f"[instagram] FAILED: {exc}")
            traceback.print_exc()

    click.echo(f"[done] publish finished for {job_id}")


@main.command("status")
@click.option("--job", "job_id", required=True)
def status_cmd(job_id: str) -> None:
    """Show job.json for a job."""
    status = load_job(job_id)
    click.echo(status.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
