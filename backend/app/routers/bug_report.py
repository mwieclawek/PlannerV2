"""Bug report endpoint - proxies to GitHub Issues API.

The GITHUB_TOKEN environment variable must be set on the server.
This keeps the token out of the frontend and repository code.
"""
import os
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth_utils import get_current_user
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["bug-report"])

GITHUB_OWNER = "mwieclawek"
GITHUB_REPO = "PlannerV2"


class BugReportRequest(BaseModel):
    title: str
    description: str
    steps_to_reproduce: str = ""


class BugReportResponse(BaseModel):
    issue_url: str
    issue_number: int


@router.post("/bug-report", response_model=BugReportResponse)
def submit_bug_report(
    report: BugReportRequest,
    current_user: User = Depends(get_current_user),
):
    """Submit a bug report which creates a GitHub Issue."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="Bug reporting is not configured. Contact your administrator.",
        )

    # Build issue body with metadata
    body_parts = [
        f"## Opis\n{report.description}",
    ]
    if report.steps_to_reproduce:
        body_parts.append(f"## Kroki do odtworzenia\n{report.steps_to_reproduce}")
    body_parts.append(
        f"---\n*Zgłoszone przez: {current_user.full_name} (`{current_user.username}`)*"
    )
    body = "\n\n".join(body_parts)

    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/issues"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "title": f"[Bug] {report.title}",
        "body": body,
        "labels": ["bug", "user-reported"],
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return BugReportResponse(
                issue_url=data["html_url"],
                issue_number=data["number"],
            )
    except httpx.HTTPStatusError as e:
        logger.error(f"GitHub API error: {e.response.status_code} {e.response.text}")
        raise HTTPException(status_code=502, detail="Failed to create GitHub issue")
    except Exception as e:
        logger.error(f"Bug report error: {e}")
        raise HTTPException(status_code=502, detail="Failed to submit bug report")
