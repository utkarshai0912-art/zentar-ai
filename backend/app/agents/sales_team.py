"""
Zentar Intelligence — Sales Automation Team

A dedicated sales pipeline that discovers leads, researches companies,
analyzes opportunities, generates personalized outreach, and manages the
entire sales process from prospecting to meeting scheduling.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.services.ai_service import provider_registry

logger = logging.getLogger("zentar.agents.sales")


class SalesLead:
    """A sales lead with research and outreach data."""

    def __init__(self, lead_id: str, company_name: str, domain: Optional[str] = None):
        self.lead_id = lead_id
        self.company_name = company_name
        self.domain = domain
        self.contacts: List[Dict[str, str]] = []
        self.company_info: Dict[str, Any] = {}
        self.website_analysis: Dict[str, Any] = {}
        self.opportunity_score: float = 0.0
        self.personalized_email: Optional[str] = None
        self.proposal: Optional[str] = None
        self.status = "new"
        self.created_at = time.time()
        self.notes: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "company_name": self.company_name,
            "domain": self.domain,
            "contacts": self.contacts,
            "opportunity_score": self.opportunity_score,
            "status": self.status,
            "created_at": self.created_at,
        }


class SalesAgent:
    """Base class for sales pipeline agents."""

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"{self.system_prompt}\n\nContext:\n{json.dumps(context, indent=2)}"
        result = ""
        async for event in provider_registry.route_request(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            stream=False,
        ):
            if event["type"] == "done":
                result = event.get("content", "")
        return {"agent": self.name, "output": result}


class LeadFinderAgent(SalesAgent):
    def __init__(self):
        super().__init__(
            name="Lead Finder Agent",
            system_prompt=(
                "You are a lead generation specialist. Given a target market or industry, "
                "identify potential business leads. For each lead, provide: company name, "
                "website domain, estimated size, and why they might be interested. "
                "Respond with a JSON array of leads."
            ),
        )


class BusinessResearchAgent(SalesAgent):
    def __init__(self):
        super().__init__(
            name="Business Research Agent",
            system_prompt=(
                "You are a business researcher. Given a company name and domain, "
                "research and describe: what they do, their industry, company size, "
                "key products/services, recent news, and potential pain points. "
                "Be specific and factual."
            ),
        )


class WebsiteAnalysisAgent(SalesAgent):
    def __init__(self):
        super().__init__(
            name="Website Analysis Agent",
            system_prompt=(
                "You are a website analyst. Given a company's website description, "
                "analyze: their value proposition, target audience, technology stack "
                "indicators, pricing model hints, and areas where they could improve. "
                "Provide actionable insights."
            ),
        )


class OpportunityDetectionAgent(SalesAgent):
    def __init__(self):
        super().__init__(
            name="Opportunity Detection Agent",
            system_prompt=(
                "You are an opportunity detector. Given company research and website analysis, "
                "score the opportunity (0-100) and explain: why this company is a good fit, "
                "what pain points our solution addresses, recommended approach, "
                "and estimated deal size potential. Output as JSON."
            ),
        )


class EmailPersonalisationAgent(SalesAgent):
    def __init__(self):
        super().__init__(
            name="Email Personalisation Agent",
            system_prompt=(
                "You are an email personalization specialist. Given lead research, "
                "craft a personalized cold outreach email that: references their specific "
                "situation, demonstrates understanding of their business, presents value "
                "proposition, includes a clear call-to-action. Keep it professional and concise."
            ),
        )


class ProposalGenerator(SalesAgent):
    def __init__(self):
        super().__init__(
            name="Proposal Generator",
            system_prompt=(
                "You are a proposal specialist. Given lead context and email conversation, "
                "generate a professional business proposal outlining: executive summary, "
                "understanding of their needs, proposed solution, pricing/options, "
                "timeline, and next steps. Format as a structured document."
            ),
        )


class SalesPipeline:
    """Orchestrates the entire sales automation pipeline."""

    def __init__(self, pipeline_id: Optional[str] = None):
        self.pipeline_id = pipeline_id or str(uuid.uuid4())
        self.leads: Dict[str, SalesLead] = {}
        self.agents = self._init_agents()
        self.status = "idle"
        self.current_step: Optional[str] = None

    def _init_agents(self) -> Dict[str, SalesAgent]:
        return {
            "lead_finder": LeadFinderAgent(),
            "business_research": BusinessResearchAgent(),
            "website_analysis": WebsiteAnalysisAgent(),
            "opportunity_detection": OpportunityDetectionAgent(),
            "email_personalization": EmailPersonalisationAgent(),
            "proposal_generator": ProposalGenerator(),
        }

    async def run_pipeline(self, target_market: str) -> List[SalesLead]:
        self.status = "running"
        leads = []

        # Step 1: Find leads
        self.current_step = "Finding leads"
        logger.info("Finding leads for: %s", target_market)
        result = await self.agents["lead_finder"].execute({"target_market": target_market})
        lead_data = self._parse_json(result.get("output", "[]"))
        for ld in (lead_data if isinstance(lead_data, list) else []):
            lead = SalesLead(
                lead_id=str(uuid.uuid4()),
                company_name=ld.get("company_name", "Unknown"),
                domain=ld.get("domain", ""),
            )
            self.leads[lead.lead_id] = lead
            leads.append(lead)

        # Steps 2-4: Research, analyze, score each lead
        for lead in leads:
            lead.status = "researching"
            ctx = {"company_name": lead.company_name, "domain": lead.domain}

            r = await self.agents["business_research"].execute(ctx)
            lead.company_info = {"research": r.get("output", "")}

            r = await self.agents["website_analysis"].execute({**ctx, "research": lead.company_info})
            lead.website_analysis = {"analysis": r.get("output", "")}

            r = await self.agents["opportunity_detection"].execute({
                **ctx, "research": lead.company_info, "analysis": lead.website_analysis
            })
            try:
                score_data = json.loads(r.get("output", "{}"))
                lead.opportunity_score = float(score_data.get("score", 50))
            except (json.JSONDecodeError, ValueError, TypeError):
                lead.opportunity_score = 50.0

            lead.status = "researched"

        # Step 5: Generate emails for high-scoring leads
        for lead in leads:
            if lead.opportunity_score >= 50:
                r = await self.agents["email_personalization"].execute(lead.to_dict())
                lead.personalized_email = r.get("output", "")

        self.status = "completed"
        return leads

    async def generate_proposal(self, lead_id: str) -> Optional[str]:
        lead = self.leads.get(lead_id)
        if not lead:
            return None
        result = await self.agents["proposal_generator"].execute(lead.to_dict())
        lead.proposal = result.get("output", "")
        return lead.proposal

    def _parse_json(self, text: str) -> Any:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []

    def get_stats(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "status": self.status,
            "total_leads": len(self.leads),
            "avg_opportunity_score": (
                sum(l.opportunity_score for l in self.leads.values()) / max(len(self.leads), 1)
            ),
        }


class SalesPipelineManager:
    """Manages multiple sales pipeline instances."""

    def __init__(self):
        self._pipelines: Dict[str, SalesPipeline] = {}

    def create_pipeline(self) -> SalesPipeline:
        p = SalesPipeline()
        self._pipelines[p.pipeline_id] = p
        return p

    def get_pipeline(self, pipeline_id: str) -> Optional[SalesPipeline]:
        return self._pipelines.get(pipeline_id)

    def list_pipelines(self) -> List[Dict[str, Any]]:
        return [p.get_stats() for p in self._pipelines.values()]


sales_pipeline_manager = SalesPipelineManager()