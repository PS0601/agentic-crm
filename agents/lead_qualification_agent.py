"""Lead Qualification Agent - Scores and routes incoming leads"""

from typing import Dict, Any
from .base_agent import BaseAgent
import re


class LeadQualificationAgent(BaseAgent):
    """
    Autonomous agent that:
    - Scores incoming leads automatically
    - Routes high-value prospects to sales
    - Enriches contact data from public sources
    - Identifies buying signals
    """

    def __init__(self, llm, tools=None, memory=None, redis_client=None):
        super().__init__(
            name="LeadQualificationAgent",
            llm=llm,
            tools=tools,
            memory=memory,
            redis_client=redis_client
        )

        # Scoring criteria weights
        self.scoring_weights = {
            "company_size": 0.25,
            "job_title": 0.25,
            "industry": 0.20,
            "engagement": 0.15,
            "budget_signals": 0.15
        }

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute lead qualification workflow"""
        lead_data = task.get("lead_data", {})

        await self.log_activity("lead_received", {"email": lead_data.get("email")})

        # Step 1: Enrich lead data
        enriched_data = await self.enrich_lead(lead_data)

        # Step 2: Score the lead
        score = await self.score_lead(enriched_data)

        # Step 3: Identify buying signals
        signals = await self.identify_buying_signals(enriched_data)

        # Step 4: Route to appropriate team
        routing = await self.route_lead(score, signals)

        # Step 5: Publish event for other agents
        await self.publish_event("lead_qualified", {
            "lead_id": enriched_data.get("id"),
            "score": score,
            "routing": routing,
            "signals": signals
        })

        result = {
            "lead_id": enriched_data.get("id"),
            "original_data": lead_data,
            "enriched_data": enriched_data,
            "score": score,
            "signals": signals,
            "routing": routing
        }

        await self.log_activity("lead_qualified", result)

        return result

    async def enrich_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich lead data from public sources"""
        email = lead_data.get("email", "")

        # Extract company domain from email
        domain = email.split("@")[-1] if "@" in email else ""

        # Use LLM to enrich data. The model has no internet access here, so the
        # prompt restricts it to the lead's own details and allows "unknown".
        name = lead_data.get("name") or " ".join(
            x for x in [lead_data.get("first_name"), lead_data.get("last_name")] if x
        ) or "Unknown"
        enrichment_prompt = f"""
        Assess this lead using ONLY the information below. You have no internet
        access, so do not invent facts about the company or person. If something
        cannot be determined from this data, answer "unknown".

        Email: {email}
        Name: {name}
        Job title: {lead_data.get('job_title') or 'not provided'}
        Company: {lead_data.get('company_name') or 'not provided'}
        Company domain: {domain}
        Message from the lead: {lead_data.get('message') or 'none'}

        Provide:
        1. Likely company size (small/medium/large/enterprise/unknown)
        2. Industry classification (or unknown)
        3. Job title seniority (entry/mid/senior/executive/unknown)
        4. Budget likelihood (low/medium/high/unknown)

        Return as JSON.
        """

        enrichment = await self.think(enrichment_prompt)

        # Merge original + enriched data
        enriched = {**lead_data}
        enriched["domain"] = domain
        enriched["enrichment"] = enrichment
        enriched["enriched_at"] = self._get_timestamp()

        return enriched

    async def score_lead(self, lead_data: Dict[str, Any]) -> int:
        """Score lead from 0-100"""

        scoring_prompt = f"""
        Score this lead from 0-100 based on qualification criteria:

        Lead Data:
        {lead_data}

        Scoring Criteria:
        - Company size (25%): Enterprise > Large > Medium > Small
        - Job title (25%): Executive > Director > Manager > Individual Contributor
        - Industry (20%): Tech, Finance, Healthcare = high value
        - Engagement (15%): Multiple touchpoints, content downloads
        - Budget signals (15%): Mentions pricing, demo requests, timeline questions

        Base the score only on the data above. Missing information should
        lower your confidence, not be filled in with guesses.

        Return ONLY the numeric score (0-100).
        """

        score_text = await self.think(scoring_prompt)

        # Extract numeric score
        score = self._extract_score(score_text)

        return score

    async def identify_buying_signals(self, lead_data: Dict[str, Any]) -> list:
        """Identify signals that indicate buying intent"""

        signals_prompt = f"""
        Identify buying signals from this lead data:

        {lead_data}

        A signal counts ONLY if something in the data backs it up: the lead's own
        message, their job title, or their stated company. Do not guess or assume.
        Possible signals:
        - Timeline mentions ("need by Q4", "urgent")
        - Budget or pricing questions
        - Demo or trial requests
        - Comparison shopping
        - Decision-maker involvement (title shows budget authority)
        - Pain point mentions

        Return a short bullet list, one signal per line, at most 5, each citing
        what it is based on. If no signal is backed by the data, return exactly: None
        """

        signals_text = await self.think(signals_prompt)

        # Parse signals
        signals = [s.strip().lstrip("-•*0123456789. ").strip() for s in signals_text.split("\n") if s.strip()]
        signals = [s for s in signals if s and s.lower() != "none"][:5]

        return signals

    async def route_lead(self, score: int, signals: list) -> Dict[str, Any]:
        """Route lead to appropriate sales team"""

        if score >= 80:
            team = "Enterprise Sales"
            priority = "high"
        elif score >= 60:
            team = "Mid-Market Sales"
            priority = "medium"
        elif score >= 40:
            team = "SMB Sales"
            priority = "medium"
        else:
            team = "Marketing Nurture"
            priority = "low"

        # High priority if urgent signals
        urgent_keywords = ["urgent", "asap", "immediately", "this week"]
        if any(keyword in " ".join(signals).lower() for keyword in urgent_keywords):
            priority = "high"

        routing = {
            "team": team,
            "priority": priority,
            "recommended_action": self._get_recommended_action(score, signals),
            "sla_hours": 24 if priority == "high" else 48 if priority == "medium" else 72
        }

        return routing

    def _extract_score(self, text: str) -> int:
        """Extract numeric score from LLM response"""
        # Look for number 0-100
        import re
        match = re.search(r'\b(\d{1,3})\b', text)
        if match:
            score = int(match.group(1))
            return min(100, max(0, score))
        return 50  # Default medium score

    def _get_recommended_action(self, score: int, signals: list) -> str:
        """Get recommended next action"""
        if score >= 80:
            return "Schedule executive demo within 24 hours"
        elif score >= 60:
            return "Send personalized email with case studies"
        elif score >= 40:
            return "Add to nurture campaign"
        else:
            return "Add to monthly newsletter"

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
