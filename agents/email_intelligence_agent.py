"""Email Intelligence Agent - Drafts personalized responses and analyzes sentiment"""

from typing import Dict, Any, List
from .base_agent import BaseAgent
import re


class EmailIntelligenceAgent(BaseAgent):
    """
    Autonomous agent that:
    - Drafts personalized email responses
    - Performs sentiment analysis on customer emails
    - Auto-categorizes and prioritizes emails
    - Provides smart follow-up suggestions
    """

    def __init__(self, llm, tools=None, memory=None, redis_client=None):
        super().__init__(
            name="EmailIntelligenceAgent",
            llm=llm,
            tools=tools,
            memory=memory,
            redis_client=redis_client
        )

        self.categories = [
            "support_request",
            "sales_inquiry",
            "demo_request",
            "pricing_question",
            "complaint",
            "feature_request",
            "general_inquiry"
        ]

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute email intelligence workflow"""
        email_data = task.get("email_data", {})

        await self.log_activity("email_received", {"from": email_data.get("from")})

        # Step 1: Analyze sentiment
        sentiment = await self.analyze_sentiment(email_data)

        # Step 2: Categorize email
        category = await self.categorize_email(email_data)

        # Step 3: Determine priority
        priority = await self.determine_priority(email_data, sentiment, category)

        # Step 4: Draft response
        draft_response = await self.draft_response(email_data, sentiment, category)

        # Step 5: Generate follow-up suggestions
        follow_ups = await self.suggest_follow_ups(email_data, category)

        # Publish event
        await self.publish_event("email_processed", {
            "email_id": email_data.get("id"),
            "sentiment": sentiment,
            "category": category,
            "priority": priority
        })

        result = {
            "email_id": email_data.get("id"),
            "sentiment": sentiment,
            "category": category,
            "priority": priority,
            "draft_response": draft_response,
            "follow_up_suggestions": follow_ups,
            "requires_human_review": priority == "high" or sentiment["score"] < 3
        }

        await self.log_activity("email_processed", result)

        return result

    async def analyze_sentiment(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze sentiment of email content"""
        content = email_data.get("body", "")
        subject = email_data.get("subject", "")

        sentiment_prompt = f"""
        Analyze the sentiment of this email:

        Subject: {subject}
        Body: {content}

        Provide:
        1. Sentiment score (1-10, where 1=very negative, 10=very positive)
        2. Sentiment label (positive/neutral/negative)
        3. Emotion detected (anger/frustration/happiness/excitement/neutral)
        4. Urgency level (low/medium/high)
        5. Key concerns or pain points

        Return ONLY a JSON object with exactly these keys:
        {{"score": <1-10>, "label": "positive|neutral|negative",
         "emotion": "anger|frustration|happiness|excitement|neutral",
         "urgency": "low|medium|high", "concerns": ["...", "..."]}}
        """

        sentiment_response = await self.think(sentiment_prompt)

        # Parse sentiment data (JSON first, then the loose text extractors)
        parsed = self._parse_sentiment_json(sentiment_response)
        if parsed:
            return parsed

        sentiment = {
            "score": self._extract_sentiment_score(sentiment_response),
            "label": self._extract_sentiment_label(sentiment_response),
            "emotion": self._extract_emotion(sentiment_response),
            "urgency": self._extract_urgency(sentiment_response),
            "concerns": self._extract_concerns(sentiment_response)
        }

        return sentiment

    async def categorize_email(self, email_data: Dict[str, Any]) -> str:
        """Categorize email into predefined categories"""
        content = email_data.get("body", "")
        subject = email_data.get("subject", "")

        categorization_prompt = f"""
        Categorize this email into ONE of these categories:
        {', '.join(self.categories)}

        Subject: {subject}
        Body: {content}

        Return ONLY the category name.
        """

        category = await self.think(categorization_prompt)
        category = category.strip().lower()

        # Validate category
        if category not in self.categories:
            category = "general_inquiry"

        return category

    async def determine_priority(
        self,
        email_data: Dict[str, Any],
        sentiment: Dict[str, Any],
        category: str
    ) -> str:
        """Determine email priority (low/medium/high)"""

        # High priority criteria
        if sentiment["urgency"] == "high":
            return "high"

        if sentiment["score"] <= 3:  # Negative sentiment
            return "high"

        if category in ["complaint", "demo_request"]:
            return "high"

        # Check for VIP sender
        sender = email_data.get("from", "")
        if await self._is_vip_sender(sender):
            return "high"

        # Medium priority
        if category in ["pricing_question", "sales_inquiry", "feature_request"]:
            return "medium"

        # Low priority
        return "low"

    async def draft_response(
        self,
        email_data: Dict[str, Any],
        sentiment: Dict[str, Any],
        category: str
    ) -> str:
        """Draft personalized email response"""

        sender_name = email_data.get("from_name", "there")
        content = email_data.get("body", "")
        subject = email_data.get("subject", "")

        # Get context from CRM
        context = await self._get_customer_context(email_data.get("from"))

        response_prompt = f"""
        Draft a professional, personalized email response:

        Original Email:
        From: {sender_name}
        Subject: {subject}
        Body: {content}

        Context:
        - Sentiment: {sentiment['label']} ({sentiment['emotion']})
        - Category: {category}
        - Customer history: {context}

        Guidelines:
        - Address concerns directly
        - Match tone to sentiment (empathetic if negative, enthusiastic if positive)
        - Provide specific next steps
        - Keep it concise (3-4 paragraphs max)
        - End with clear call-to-action

        Draft the email response:
        """

        draft = await self.think(response_prompt)

        return draft

    async def suggest_follow_ups(
        self,
        email_data: Dict[str, Any],
        category: str
    ) -> List[str]:
        """Generate smart follow-up suggestions"""

        suggestions_prompt = f"""
        Suggest 3 follow-up actions for this email:

        Category: {category}
        Email: {email_data.get('body', '')[:200]}

        Provide specific, actionable follow-ups like:
        - Schedule demo call
        - Send pricing sheet
        - Connect with technical team
        - Add to nurture campaign

        Return as numbered list.
        """

        suggestions_text = await self.think(suggestions_prompt)

        # Parse suggestions
        suggestions = [
            s.strip() for s in suggestions_text.split("\n")
            if s.strip() and any(c.isalpha() for c in s)
        ][:3]

        return suggestions

    async def _is_vip_sender(self, email: str) -> bool:
        """Check if sender is VIP customer"""
        # Query CRM database for VIP status
        # Placeholder implementation
        vip_domains = ["enterprise.com", "bigclient.com"]
        domain = email.split("@")[-1] if "@" in email else ""
        return domain in vip_domains

    async def _get_customer_context(self, email: str) -> str:
        """Get customer history from CRM"""
        # Query CRM for past interactions
        # Placeholder implementation
        return "First-time contact, no previous interactions"

    def _parse_sentiment_json(self, text: str):
        """Parse a JSON sentiment reply; returns None if it is not valid JSON."""
        import json
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            data = json.loads(cleaned[start:end + 1])
        except ValueError:
            return None
        try:
            score = max(1, min(10, int(data.get("score"))))
        except (TypeError, ValueError):
            return None
        label = str(data.get("label", "neutral")).lower()
        if label not in ("positive", "neutral", "negative"):
            label = "neutral"
        emotion = str(data.get("emotion", "neutral")).lower()
        if emotion not in ("anger", "frustration", "happiness", "excitement", "neutral"):
            emotion = "neutral"
        urgency = str(data.get("urgency", "medium")).lower()
        if urgency not in ("low", "medium", "high"):
            urgency = "medium"
        concerns = [str(c) for c in (data.get("concerns") or [])][:3]
        return {"score": score, "label": label, "emotion": emotion,
                "urgency": urgency, "concerns": concerns}

    def _extract_sentiment_score(self, text: str) -> int:
        """Extract sentiment score from LLM response"""
        match = re.search(r'score["\s:]+(\d+)', text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 5  # Neutral default

    def _extract_sentiment_label(self, text: str) -> str:
        """Extract sentiment label"""
        text_lower = text.lower()
        if "positive" in text_lower:
            return "positive"
        elif "negative" in text_lower:
            return "negative"
        return "neutral"

    def _extract_emotion(self, text: str) -> str:
        """Extract detected emotion"""
        emotions = ["anger", "frustration", "happiness", "excitement", "neutral"]
        text_lower = text.lower()
        for emotion in emotions:
            if emotion in text_lower:
                return emotion
        return "neutral"

    def _extract_urgency(self, text: str) -> str:
        """Extract urgency level"""
        text_lower = text.lower()
        if "high" in text_lower:
            return "high"
        elif "low" in text_lower:
            return "low"
        return "medium"

    def _extract_concerns(self, text: str) -> List[str]:
        """Extract key concerns from analysis"""
        # Simple extraction - look for bullet points or numbered items
        concerns = []
        lines = text.split("\n")
        for line in lines:
            if any(marker in line for marker in ["-", "•", "concern", "pain point"]):
                concern = line.strip().lstrip("-•").strip()
                if concern:
                    concerns.append(concern)
        return concerns[:3]  # Top 3 concerns
