#!/usr/bin/env python3
"""Fill the database with realistic demo data so the dashboard is not empty.

    python seed_demo.py            # seeds only if the database is empty
    python seed_demo.py --reset    # wipes ALL CRM tables first, then seeds

All people and companies are fictional.
"""

import sys
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

from database.connection import engine, SessionLocal  # noqa: E402
from database.models import Base, Company, Contact, Customer, Deal, Email  # noqa: E402

NOW = datetime.now(timezone.utc).replace(tzinfo=None)
TODAY = date.today()


def days_ago(n):
    return NOW - timedelta(days=n)


def in_days(n):
    return TODAY + timedelta(days=n)


COMPANIES = [
    # key, name, domain, industry, size, location
    ("northwind", "Northwind Logistics", "northwind-logistics.example", "Logistics", "1000+", "Chicago, IL"),
    ("helix", "Helix Biotech", "helixbio.example", "Healthcare", "201-1000", "Boston, MA"),
    ("lumen", "Lumen Analytics", "lumen-analytics.example", "Technology", "51-200", "Austin, TX"),
    ("brightpath", "Brightpath Education", "brightpath.example", "Education", "51-200", "Denver, CO"),
    ("cobalt", "Cobalt Financial", "cobaltfin.example", "Finance", "1000+", "New York, NY"),
    ("orbit", "Orbit Retail", "orbitretail.example", "Retail", "201-1000", "Seattle, WA"),
    ("meridian", "Meridian Health Group", "meridianhealth.example", "Healthcare", "1000+", "Atlanta, GA"),
    ("atlas", "Atlas Manufacturing", "atlasmfg.example", "Manufacturing", "201-1000", "Detroit, MI"),
    ("fernwood", "Fernwood Hospitality", "fernwood.example", "Hospitality", "51-200", "Portland, OR"),
    ("quanta", "Quanta Cloud", "quantacloud.example", "Technology", "201-1000", "San Francisco, CA"),
    ("verdant", "Verdant Energy", "verdant-energy.example", "Energy", "201-1000", "Houston, TX"),
    ("pioneer", "Pioneer Insurance", "pioneerins.example", "Finance", "1000+", "Hartford, CT"),
]

# company, first, last, email local, title, level, score, source, days since created
LEADS = [
    ("cobalt", "Priya", "Raman", "priya.raman", "Chief Technology Officer", "executive", 92, "Referral", 3),
    ("northwind", "Marcus", "Webb", "marcus.webb", "VP of Operations", "executive", 88, "Demo request", 5),
    ("quanta", "Elena", "Fischer", "elena.fischer", "Director of Engineering", "director", 84, "Webinar", 6),
    ("meridian", "James", "Okafor", "james.okafor", "VP of Digital Transformation", "executive", 81, "Conference", 8),
    ("helix", "Sofia", "Lindqvist", "sofia.lindqvist", "Head of Data", "director", 76, "Content download", 4),
    ("pioneer", "Daniel", "Cho", "daniel.cho", "Director of Customer Experience", "director", 72, "Website form", 9),
    ("orbit", "Hannah", "Brooks", "hannah.brooks", "Senior Marketing Manager", "manager", 66, "Website form", 2),
    ("atlas", "Luis", "Navarro", "luis.navarro", "Plant Operations Manager", "manager", 63, "Trade show", 12),
    ("verdant", "Amara", "Singh", "amara.singh", "Head of Procurement", "director", 61, "Outbound", 7),
    ("lumen", "Ethan", "Park", "ethan.park", "Product Manager", "manager", 58, "Webinar", 1),
    ("brightpath", "Grace", "Holloway", "grace.holloway", "Operations Manager", "manager", 54, "Website form", 10),
    ("fernwood", "Tomas", "Reyes", "tomas.reyes", "General Manager", "manager", 49, "Referral", 14),
    ("orbit", "Nina", "Kowalski", "nina.kowalski", "Marketing Coordinator", "individual", 41, "Content download", 11),
    ("lumen", "Oliver", "Grant", "oliver.grant", "Data Analyst", "individual", 38, "Webinar", 16),
    ("atlas", "Ravi", "Menon", "ravi.menon", "Maintenance Technician", "individual", 27, "Trade show", 20),
    ("brightpath", "Chloe", "Dubois", "chloe.dubois", "Teaching Assistant", "individual", 18, "Website form", 18),
]


def team_for(score):
    if score >= 80:
        return "Enterprise Sales"
    if score >= 60:
        return "Mid-Market Sales"
    if score >= 40:
        return "SMB Sales"
    return "Marketing Nurture"


# name, company, contact email local, stage, value, probability, health, stalled, close in days, notes
DEALS = [
    ("Cobalt Financial - platform rollout", "cobalt", "priya.raman", "negotiation", 185000, 75, 82, False, 18,
     "Legal review of MSA in progress. Champion is the CTO."),
    ("Northwind - dispatch automation", "northwind", "marcus.webb", "proposal", 142000, 55, 74, False, 35,
     "Proposal sent; waiting on budget sign-off from finance."),
    ("Meridian Health - intake workflow", "meridian", "james.okafor", "qualification", 96000, 35, 61, False, 60,
     "Security questionnaire requested before the next call."),
    ("Quanta Cloud - agent pilot", "quanta", "elena.fischer", "proposal", 64000, 50, 70, False, 28,
     "Three-month pilot; success criteria agreed."),
    ("Pioneer Insurance - claims triage", "pioneer", "daniel.cho", "prospecting", 120000, 20, 55, False, 90,
     "Early conversations; needs executive sponsor."),
    ("Helix Biotech - research assistant", "helix", "sofia.lindqvist", "negotiation", 78000, 70, 79, False, 12,
     "Pricing agreed, finalizing data-processing terms."),
    ("Atlas Manufacturing - quality alerts", "atlas", "luis.navarro", "proposal", 52000, 40, 38, True, 40,
     "No reply to the last two follow-ups (23 days)."),
    ("Verdant Energy - supplier portal", "verdant", "amara.singh", "qualification", 41000, 30, 44, True, 75,
     "Stalled in procurement; no activity for 19 days."),
    ("Orbit Retail - campaign insights", "orbit", "hannah.brooks", "prospecting", 28000, 15, 58, False, 80, None),
    ("Lumen Analytics - team seats", "lumen", "ethan.park", "qualification", 19000, 30, 66, False, 45, None),
    ("Brightpath Education - annual plan", "brightpath", None, "closed_won", 24000, 100, 95, False, -20, "Signed; onboarding done."),
    ("Fernwood Hospitality - booking assistant", "fernwood", None, "closed_won", 36000, 100, 92, False, -45, "Signed after a 2-week pilot."),
    ("Northwind - fleet pilot", "northwind", None, "closed_won", 58000, 100, 90, False, -70, "Expanded into the main deal above."),
    ("Atlas Manufacturing - legacy migration", "atlas", None, "closed_lost", 47000, 0, 20, False, -30, "Lost to an in-house build."),
]

# company, plan, mrr, health, churn risk, churn prob, logins/wk, features used, license %, tickets, nps
CUSTOMERS = [
    ("northwind", "Enterprise", 9800, 91, "low", 5, 42, 9, 88, 1, 62),
    ("fernwood", "Growth", 3000, 88, "low", 8, 24, 7, 81, 0, 55),
    ("brightpath", "Growth", 2000, 84, "low", 10, 19, 6, 74, 2, 48),
    ("cobalt", "Enterprise", 14200, 72, "medium", 28, 31, 7, 63, 4, 31),
    ("meridian", "Enterprise", 11500, 58, "medium", 41, 17, 5, 52, 6, 18),
    ("orbit", "Starter", 900, 49, "high", 62, 6, 3, 34, 5, 4),
    ("atlas", "Growth", 2600, 35, "high", 78, 3, 2, 22, 9, -12),
    ("verdant", "Starter", 750, 66, "medium", 33, 11, 4, 47, 3, 22),
]

# from, subject, body, sentiment, score, emotion, category, priority, draft
EMAILS = [
    ("m.webb@northwind-logistics.example", "Dispatch module - going live Monday",
     "Hi team, the dispatch module has been great in testing. Our ops leads are excited and we want to go live Monday. Can we get a quick walkthrough for the night shift?",
     "positive", 9, "excitement", "support_request", "medium",
     "Hi Marcus,\n\nThat is great to hear, and congratulations on getting to go-live. I can run a 30-minute walkthrough for the night shift on Friday at 4pm or Saturday morning, whichever suits your leads. I will also send a one-page quick-start guide today.\n\nWhich slot works best?\n\nBest,\nCustomer Success"),
    ("a.navarro@atlasmfg.example", "Alerts keep failing - we are losing patience",
     "This is the third time this month that quality alerts have not fired. Our line supervisors are now ignoring the system. If this is not fixed this week we will look at cancelling.",
     "negative", 2, "anger", "complaint", "high",
     "Hi Luis,\n\nI am sorry - missed alerts on a production line are not acceptable, and you are right to be frustrated. I have escalated this to our engineering lead and will personally update you by end of day tomorrow with the root cause and a fix date.\n\nCould you share two or three timestamps of alerts that did not fire so we can trace them?\n\nRegards,\nCustomer Success"),
    ("daniel.cho@pioneerins.example", "Pricing for 500 seats",
     "We are evaluating options for claims triage. Could you send pricing for roughly 500 seats and tell us whether you support SSO and audit logs?",
     "neutral", 6, "neutral", "pricing_question", "medium",
     "Hi Daniel,\n\nThanks for reaching out. Yes - SSO (SAML) and full audit logs are included on our Enterprise plan. For 500 seats I would like to put together a tailored quote; could we spend 20 minutes this week to confirm your volume and rollout timeline?\n\nBest,\nSales"),
    ("priya.raman@cobaltfin.example", "Intro to our security team",
     "Thanks for the great demo yesterday. I would like to introduce you to our CISO before we move to contract.",
     "positive", 8, "happiness", "sales_inquiry", "high",
     "Hi Priya,\n\nThank you - I am glad the demo landed well. I would be happy to meet your CISO. I will send our security whitepaper and SOC 2 report ahead of time so the call can focus on your specific questions.\n\nHow does Thursday afternoon look?\n\nBest,\nSales"),
    ("hannah.brooks@orbitretail.example", "Can reports be exported to Excel?",
     "Quick question - is there a way to export the campaign report to Excel? We have been copying it by hand.",
     "neutral", 6, "neutral", "feature_request", "low",
     "Hi Hannah,\n\nGood question. CSV export is available from the report page today (top-right menu), and it opens directly in Excel. A native .xlsx export is on our roadmap and I have added your vote for it.\n\nLet me know if the CSV works for now.\n\nBest,\nSupport"),
    ("grace.holloway@brightpath.example", "Thank you!",
     "Just wanted to say the onboarding was excellent. Our team picked it up in a day.",
     "positive", 10, "happiness", "general_inquiry", "low",
     "Hi Grace,\n\nThat made my day - thank you! I will pass your kind words to the onboarding team. If your team ever wants to go deeper on reporting or automation, we are happy to run a short workshop.\n\nBest,\nCustomer Success"),
    ("amara.singh@verdant-energy.example", "Following up on procurement",
     "Procurement is asking for a W-9 and a vendor security form. Can you send both? We have been delayed by a reorganisation.",
     "neutral", 5, "neutral", "support_request", "medium",
     "Hi Amara,\n\nNo problem - I have attached our W-9 and the completed vendor security form. If procurement needs anything else, send me the checklist and I will turn it around within a day.\n\nBest,\nSales"),
    ("j.okafor@meridianhealth.example", "Concerns about onboarding timeline",
     "We expected to be live by now. Support responses have been slow and I am worried we will miss our quarter-end target.",
     "negative", 3, "frustration", "complaint", "high",
     "Hi James,\n\nThank you for being direct about this. I am sorry the timeline and our response times have not met expectations. I have asked our implementation lead to join a call with you tomorrow to agree a dated plan to get you live before quarter-end.\n\nWould 10am or 2pm work?\n\nRegards,\nCustomer Success"),
]


def main():
    reset = "--reset" in sys.argv
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if reset:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()
            print("Cleared all CRM tables.")
        elif db.query(Contact).count() > 0 or db.query(Deal).count() > 0:
            print("Database already has data - skipping. Use --reset to wipe and re-seed.")
            return

        companies = {}
        for key, name, domain, industry, size, location in COMPANIES:
            c = Company(name=name, domain=domain, industry=industry, company_size=size, location=location)
            db.add(c)
            companies[key] = c
        db.flush()

        contacts = {}
        for key, first, last, local, title, level, score, source, age in LEADS:
            company = companies[key]
            contact = Contact(
                company_id=company.id,
                email=f"{local}@{company.domain}",
                first_name=first,
                last_name=last,
                job_title=title,
                job_level=level,
                lead_score=score,
                lead_status=team_for(score),
                lead_source=source,
                created_at=days_ago(age),
            )
            db.add(contact)
            contacts[local] = contact
        db.flush()

        for name, key, contact_local, stage, value, prob, health, stalled, close, notes in DEALS:
            contact = contacts.get(contact_local)
            deal = Deal(
                name=name,
                company_id=companies[key].id,
                contact_id=contact.id if contact else None,
                stage=stage,
                value=value,
                probability=prob,
                health_score=health,
                is_stalled=stalled,
                notes=notes,
                created_at=days_ago(40),
            )
            if stage in ("closed_won", "closed_lost"):
                deal.actual_close_date = in_days(close)
            else:
                deal.expected_close_date = in_days(close)
            db.add(deal)

        for key, plan, mrr, health, risk, prob, logins, used, usage, tickets, nps in CUSTOMERS:
            db.add(
                Customer(
                    company_id=companies[key].id,
                    plan=plan,
                    mrr=mrr,
                    arr=mrr * 12,
                    health_score=health,
                    churn_risk=risk,
                    churn_probability=prob,
                    logins_per_week=logins,
                    features_used=used,
                    total_features=10,
                    license_usage_percent=usage,
                    support_tickets_30d=tickets,
                    nps_score=nps,
                    contract_start_date=in_days(-200),
                    contract_end_date=in_days(165),
                )
            )

        for i, (sender, subject, body, sent, score, emotion, cat, prio, draft) in enumerate(EMAILS):
            db.add(
                Email(
                    from_email=sender,
                    subject=subject,
                    body=body,
                    direction="inbound",
                    sentiment=sent,
                    sentiment_score=score,
                    emotion=emotion,
                    category=cat,
                    priority=prio,
                    draft_response=draft,
                    received_at=days_ago(i),
                    created_at=days_ago(i),
                )
            )

        db.commit()
        print(
            f"Seeded {len(COMPANIES)} companies, {len(LEADS)} leads, {len(DEALS)} deals, "
            f"{len(CUSTOMERS)} customers, {len(EMAILS)} emails."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
