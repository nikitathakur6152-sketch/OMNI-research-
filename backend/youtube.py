import re
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    VideoUnplayable,
    AgeRestricted,
    IpBlocked,
    RequestBlocked,
    PoTokenRequired,
)

def video_id(url: str) -> str:
    patterns = [
        r"(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Provide a valid YouTube URL.")

def transcript_for(url: str):
    vid = video_id(url)
    api = YouTubeTranscriptApi()
    try:
        transcript = api.fetch(vid, languages=["en"])
    except NoTranscriptFound:
        try:
            available = api.list(vid)
            try:
                selected = available.find_transcript(["en"])
            except NoTranscriptFound:
                selected = next(iter(available))
            transcript = selected.fetch()
        except (TranscriptsDisabled, NoTranscriptFound, StopIteration) as exc:
            raise ValueError("This video has no captions available to read.") from exc
        except Exception as exc:
            raise ValueError(f"Could not retrieve this video's captions ({type(exc).__name__}).") from exc
    except TranscriptsDisabled as exc:
        raise ValueError("This video has captions disabled.") from exc
    except (VideoUnavailable, VideoUnplayable, AgeRestricted) as exc:
        raise ValueError("This video is unavailable to the transcript service, possibly because it is private, age-restricted, or region-restricted.") from exc
    except (IpBlocked, RequestBlocked) as exc:
        raise ValueError("YouTube is temporarily blocking transcript requests from this network. Try again later.") from exc
    except PoTokenRequired as exc:
        raise ValueError("YouTube requires an additional verification token for this video, so its captions cannot be fetched right now.") from exc
    except Exception as exc:
        raise ValueError(f"Could not retrieve this video's captions ({type(exc).__name__}).") from exc
    lines = []
    for item in transcript:
        text = getattr(item, "text", None) if not isinstance(item, dict) else item.get("text")
        start = getattr(item, "start", None) if not isinstance(item, dict) else item.get("start")
        if text:
            prefix = f"[{int(start)//60:02d}:{int(start)%60:02d}] " if start is not None else ""
            lines.append(prefix + text)
    if not lines:
        raise ValueError("No transcript text was returned.")
    return vid, "\n".join(lines)[:45000]
