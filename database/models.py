"""SQLAlchemy ORM Models for AI CRM"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    Text, ForeignKey, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class Company(Base):
    __tablename__ = 'companies'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True)
    industry = Column(String(100))
    company_size = Column(String(50))
    revenue_range = Column(String(50))
    location = Column(String(255))
    timezone = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    enrichment_data = Column(JSONB)
    extra_metadata = Column("metadata", JSONB)

    # Relationships
    contacts = relationship("Contact", back_populates="company")
    deals = relationship("Deal", back_populates="company")
    customers = relationship("Customer", back_populates="company")


class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'))
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    job_title = Column(String(255))
    job_level = Column(String(50))
    phone = Column(String(50))
    linkedin_url = Column(String(500))

    # Lead Qualification
    lead_score = Column(Integer, default=0)
    lead_status = Column(String(50), default='new')
    lead_source = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_contact_at = Column(DateTime)

    # Enrichment
    enrichment_data = Column(JSONB)
    extra_metadata = Column("metadata", JSONB)

    # Relationships
    company = relationship("Company", back_populates="contacts")
    deals = relationship("Deal", back_populates="contact")
    emails = relationship("Email", back_populates="contact")
    activities = relationship("Activity", back_populates="contact")

    __table_args__ = (
        CheckConstraint('lead_score >= 0 AND lead_score <= 100', name='check_lead_score'),
    )


class Deal(Base):
    __tablename__ = 'deals'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'))
    contact_id = Column(UUID(as_uuid=True), ForeignKey('contacts.id'))

    # Deal Information
    name = Column(String(255), nullable=False)
    value = Column(Float, default=0)
    stage = Column(String(50), nullable=False)
    probability = Column(Integer, default=50)

    # Health & Risk
    health_score = Column(Integer, default=50)
    is_stalled = Column(Boolean, default=False)
    risk_factors = Column(JSONB)

    # Dates
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    stage_changed_at = Column(DateTime, server_default=func.now())
    expected_close_date = Column(Date)
    actual_close_date = Column(Date)

    # Assignment
    owner_id = Column(UUID(as_uuid=True))

    # Additional
    notes = Column(Text)
    extra_metadata = Column("metadata", JSONB)

    # Relationships
    company = relationship("Company", back_populates="deals")
    contact = relationship("Contact", back_populates="deals")
    meetings = relationship("Meeting", back_populates="deal")
    activities = relationship("Activity", back_populates="deal")

    __table_args__ = (
        CheckConstraint('probability >= 0 AND probability <= 100', name='check_probability'),
        CheckConstraint('health_score >= 0 AND health_score <= 100', name='check_health_score'),
    )


class Customer(Base):
    __tablename__ = 'customers'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey('companies.id'))

    # Subscription
    plan = Column(String(100))
    mrr = Column(Float, default=0)
    arr = Column(Float, default=0)
    contract_start_date = Column(Date)
    contract_end_date = Column(Date)

    # Health Metrics
    health_score = Column(Integer, default=50)
    churn_risk = Column(String(50), default='low')
    churn_probability = Column(Integer, default=0)

    # Engagement
    last_login_at = Column(DateTime)
    logins_per_week = Column(Integer, default=0)
    features_used = Column(Integer, default=0)
    total_features = Column(Integer, default=10)
    license_usage_percent = Column(Integer, default=0)
    daily_active_users = Column(Integer, default=0)

    # Support
    support_tickets_30d = Column(Integer, default=0)
    critical_tickets_open = Column(Integer, default=0)
    avg_resolution_hours = Column(Integer, default=24)
    csat_score = Column(Float, default=0)
    nps_score = Column(Integer, default=0)

    # Payments
    last_payment_at = Column(DateTime)
    payment_delays = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    extra_metadata = Column("metadata", JSONB)

    # Relationships
    company = relationship("Company", back_populates="customers")

    __table_args__ = (
        CheckConstraint('health_score >= 0 AND health_score <= 100', name='check_customer_health_score'),
    )


class Email(Base):
    __tablename__ = 'emails'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey('contacts.id'))

    # Email Data
    from_email = Column(String(255))
    to_email = Column(String(255))
    subject = Column(Text)
    body = Column(Text)
    direction = Column(String(20))

    # AI Analysis
    sentiment = Column(String(50))
    sentiment_score = Column(Integer)
    emotion = Column(String(50))
    category = Column(String(100))
    priority = Column(String(20))

    # Response
    draft_response = Column(Text)
    response_sent = Column(Boolean, default=False)

    # Timestamps
    received_at = Column(DateTime)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    extra_metadata = Column("metadata", JSONB)

    # Relationships
    contact = relationship("Contact", back_populates="emails")


class Meeting(Base):
    __tablename__ = 'meetings'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id = Column(UUID(as_uuid=True), ForeignKey('deals.id'))

    # Meeting Info
    title = Column(String(255), nullable=False)
    meeting_type = Column(String(50))
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    location = Column(String(500))

    # Attendees
    attendees = Column(JSONB)

    # Preparation
    agenda = Column(JSONB)
    prep_materials = Column(JSONB)
    context = Column(JSONB)

    # Follow-up
    notes = Column(Text)
    followup_tasks = Column(JSONB)
    recording_url = Column(String(500))

    # Status
    status = Column(String(50), default='scheduled')

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    extra_metadata = Column("metadata", JSONB)

    # Relationships
    deal = relationship("Deal", back_populates="meetings")


class Activity(Base):
    __tablename__ = 'activities'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey('contacts.id'))
    deal_id = Column(UUID(as_uuid=True), ForeignKey('deals.id'))

    # Activity Info
    activity_type = Column(String(100))
    subject = Column(String(255))
    description = Column(Text)
    outcome = Column(String(100))

    # Assignment
    assigned_to = Column(UUID(as_uuid=True))
    completed = Column(Boolean, default=False)

    # Dates
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    extra_metadata = Column("metadata", JSONB)

    # Relationships
    contact = relationship("Contact", back_populates="activities")
    deal = relationship("Deal", back_populates="activities")


class AgentLog(Base):
    __tablename__ = 'agent_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), nullable=False)
    activity_type = Column(String(100))
    details = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now())


class AgentEvent(Base):
    __tablename__ = 'agent_events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    source_agent = Column(String(100))
    target_agent = Column(String(100))
    payload = Column(JSONB)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class MetricsDaily(Base):
    __tablename__ = 'metrics_daily'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_date = Column(Date, nullable=False, unique=True)

    # Sales Metrics
    leads_total = Column(Integer, default=0)
    leads_qualified = Column(Integer, default=0)
    deals_created = Column(Integer, default=0)
    deals_won = Column(Integer, default=0)
    deals_lost = Column(Integer, default=0)
    revenue_won = Column(Float, default=0)

    # Customer Metrics
    customers_total = Column(Integer, default=0)
    customers_churned = Column(Integer, default=0)
    mrr_total = Column(Float, default=0)
    arr_total = Column(Float, default=0)

    # Pipeline Metrics
    pipeline_value = Column(Float, default=0)
    avg_deal_size = Column(Float, default=0)
    avg_sales_cycle_days = Column(Integer, default=0)

    # Success Metrics
    avg_health_score = Column(Integer, default=0)
    avg_nps_score = Column(Integer, default=0)
    avg_csat_score = Column(Float, default=0)

    created_at = Column(DateTime, server_default=func.now())
