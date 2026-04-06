"""
Legal Document Templates Generator.

This module provides document template generation for:
- GDPR consent forms in Romanian
- EU employment contract templates
- Data sharing agreements
- Compliance checklists and reports
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader, Template
import os
from pathlib import Path

from ..database.models import Worker, Employer, ANOFMEvent
from config import get_config


@dataclass
class DocumentData:
    """Data structure for document generation."""
    worker: Optional[Dict[str, Any]] = None
    employer: Optional[Dict[str, Any]] = None
    event: Optional[Dict[str, Any]] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceChecklist:
    """Structured compliance checklist for events."""
    event_id: int
    event_name: str
    categories: Dict[str, Any]
    completion_percentage: float
    generated_at: str


class DocumentTemplates:
    """Legal document template generator."""

    def __init__(self):
        self.config = get_config()

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )

    def generate_gdpr_consent_form(self, worker_data: Dict[str, Any]) -> str:
        """Generate GDPR consent form in Romanian."""
        template_data = {
            "worker_name": f"{worker_data.get('first_name', '')} {worker_data.get('last_name', '')}".strip(),
            "worker_email": worker_data.get('email', ''),
            "current_date": datetime.now().strftime("%d/%m/%Y"),
            "data_controller": self.config.gdpr.data_controller,
            "data_controller_address": self.config.gdpr.data_controller_address,
            "privacy_policy_url": self.config.gdpr.privacy_policy_url,
            "retention_period_years": self.config.gdpr.worker_data_retention_days // 365,
            "consent_version": "1.0"
        }

        try:
            template = self.jinja_env.get_template("gdpr_consent_form.html")
            return template.render(**template_data)
        except Exception as e:
            # Fallback to inline template if file not found
            return self._get_fallback_gdpr_template().render(**template_data)

    def generate_worker_contract_template(self,
                                        worker_data: Dict[str, Any],
                                        employer_data: Dict[str, Any],
                                        job_details: Dict[str, Any]) -> str:
        """Generate EU employment contract template."""
        template_data = {
            "worker_name": f"{worker_data.get('first_name', '')} {worker_data.get('last_name', '')}".strip(),
            "worker_address": f"{worker_data.get('city', '')}, {worker_data.get('region', '')}, Romania".strip(', '),
            "employer_name": employer_data.get('name', ''),
            "employer_address": employer_data.get('address', ''),
            "employer_country": employer_data.get('country', ''),
            "job_title": job_details.get('title', ''),
            "job_description": job_details.get('description', ''),
            "salary": job_details.get('salary', ''),
            "currency": job_details.get('currency', 'EUR'),
            "work_location": job_details.get('location', ''),
            "start_date": job_details.get('start_date', ''),
            "contract_duration": job_details.get('duration', 'Indefinite'),
            "working_hours": job_details.get('working_hours', '40 hours per week'),
            "current_date": datetime.now().strftime("%d/%m/%Y"),
            "probation_period": job_details.get('probation_period', '3 months'),
            "notice_period": job_details.get('notice_period', '30 days'),
            "vacation_days": job_details.get('vacation_days', '21 days per year')
        }

        try:
            template = self.jinja_env.get_template("worker_contract_template.html")
            return template.render(**template_data)
        except Exception as e:
            # Fallback to inline template if file not found
            return self._get_fallback_contract_template().render(**template_data)

    def generate_data_sharing_agreement(self,
                                      employer_data: Dict[str, Any],
                                      event_data: Dict[str, Any]) -> str:
        """Generate data sharing agreement for employers."""
        template_data = {
            "employer_name": employer_data.get('name', ''),
            "employer_country": employer_data.get('country', ''),
            "employer_contact": employer_data.get('contact_person', ''),
            "event_name": event_data.get('name', ''),
            "event_date": event_data.get('date', ''),
            "data_controller": self.config.gdpr.data_controller,
            "data_controller_address": self.config.gdpr.data_controller_address,
            "current_date": datetime.now().strftime("%d/%m/%Y"),
            "retention_period": self.config.gdpr.worker_data_retention_days // 365,
            "privacy_policy_url": self.config.gdpr.privacy_policy_url
        }

        return self._get_data_sharing_template().render(**template_data)

    def generate_compliance_report(self, compliance_data: Dict[str, Any]) -> str:
        """Generate compliance status report."""
        template_data = {
            "event_name": compliance_data.get('event_name', ''),
            "event_date": compliance_data.get('event_date', ''),
            "completion_percentage": compliance_data.get('completion_percentage', 0),
            "categories": compliance_data.get('compliance_categories', {}),
            "summary": compliance_data.get('summary', {}),
            "generated_at": compliance_data.get('generated_at', datetime.now().isoformat()),
            "report_date": datetime.now().strftime("%d/%m/%Y %H:%M")
        }

        return self._get_compliance_report_template().render(**template_data)

    def _get_fallback_gdpr_template(self) -> Template:
        """Fallback GDPR consent form template."""
        template_content = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Formular de Consimțământ GDPR</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .section { margin-bottom: 20px; }
        .checkbox { margin: 10px 0; }
        .signature { margin-top: 40px; border-top: 1px solid #ccc; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>FORMULAR DE CONSIMȚĂMÂNT GDPR</h1>
        <h2>Prelucrarea Datelor Personale pentru Plasarea în Muncă în UE</h2>
    </div>

    <div class="section">
        <h3>Date Personale</h3>
        <p><strong>Nume și Prenume:</strong> {{ worker_name }}</p>
        <p><strong>Email:</strong> {{ worker_email }}</p>
        <p><strong>Data:</strong> {{ current_date }}</p>
    </div>

    <div class="section">
        <h3>Operator de Date</h3>
        <p><strong>{{ data_controller }}</strong></p>
        <p>{{ data_controller_address }}</p>
        <p>În calitate de operator de date conform GDPR (Regulamentul UE 2016/679)</p>
    </div>

    <div class="section">
        <h3>Scopul Prelucrării</h3>
        <p>Datele dvs. personale vor fi prelucrate în următoarele scopuri:</p>
        <ul>
            <li>Facilitarea plasării în muncă în țările membre UE</li>
            <li>Comunicarea cu potențiali angajatori europeni</li>
            <li>Organizarea și participarea la burse de munca ANOFM</li>
            <li>Îndeplinirea obligațiilor legale în materie de plasare transfrontalieră</li>
        </ul>
    </div>

    <div class="section">
        <h3>Categorii de Date Prelucrate</h3>
        <ul>
            <li>Date de identificare (nume, prenume, email, telefon)</li>
            <li>Date profesionale (experiență, competențe, educație)</li>
            <li>Preferințe de mobilitate și țări de destinație</li>
            <li>Informații despre familia și dependenți (dacă aplicabil)</li>
        </ul>
    </div>

    <div class="section">
        <h3>Perioada de Păstrare</h3>
        <p>Datele vor fi păstrate pentru o perioadă de <strong>{{ retention_period_years }} ani</strong> de la data acordării consimțământului, conform legislației în vigoare.</p>
    </div>

    <div class="section">
        <h3>Drepturile Dvs.</h3>
        <p>Aveți următoarele drepturi conform GDPR:</p>
        <ul>
            <li>Dreptul de acces la datele personale</li>
            <li>Dreptul de rectificare a datelor inexacte</li>
            <li>Dreptul de ștergere ("dreptul de a fi uitat")</li>
            <li>Dreptul de limitare a prelucrării</li>
            <li>Dreptul la portabilitatea datelor</li>
            <li>Dreptul de opoziție la prelucrare</li>
            <li>Dreptul de a vă retrage consimțământul oricând</li>
        </ul>
    </div>

    <div class="section">
        <h3>Transferuri Internaționale</h3>
        <p>Datele pot fi transferate către angajatori din țările UE în baza deciziilor de adecvare sau a clauzelor contractuale standard aprobate de Comisia Europeană.</p>
    </div>

    <div class="section">
        <h3>Consimțământ</h3>
        <div class="checkbox">
            <input type="checkbox" id="gdpr_consent" name="gdpr_consent" required>
            <label for="gdpr_consent">
                <strong>Sunt de acord cu prelucrarea datelor mele personale în scopurile menționate mai sus și confirm că am fost informat(ă) despre drepturile mele conform GDPR.</strong>
            </label>
        </div>
        <div class="checkbox">
            <input type="checkbox" id="marketing_consent" name="marketing_consent">
            <label for="marketing_consent">
                Sunt de acord să primesc comunicări de marketing despre oportunități de muncă în UE (opțional).
            </label>
        </div>
    </div>

    <div class="signature">
        <div style="display: flex; justify-content: space-between;">
            <div>
                <p>Data: _______________</p>
                <p>Semnătura: _______________</p>
            </div>
            <div>
                <p><small>Versiunea consimțământului: {{ consent_version }}</small></p>
                <p><small>Pentru informații despre protecția datelor: <a href="{{ privacy_policy_url }}">{{ privacy_policy_url }}</a></small></p>
            </div>
        </div>
    </div>
</body>
</html>
"""
        return Template(template_content)

    def _get_fallback_contract_template(self) -> Template:
        """Fallback EU employment contract template."""
        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EU Employment Contract</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
        .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #333; padding-bottom: 20px; }
        .section { margin-bottom: 25px; }
        .parties { display: flex; justify-content: space-between; }
        .party { width: 45%; }
        .signature-section { margin-top: 50px; display: flex; justify-content: space-between; }
        .signature { text-align: center; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>EUROPEAN UNION EMPLOYMENT CONTRACT</h1>
        <h3>In accordance with EU Directive 91/533/EEC</h3>
    </div>

    <div class="section">
        <h3>CONTRACTING PARTIES</h3>
        <div class="parties">
            <div class="party">
                <h4>EMPLOYER</h4>
                <p><strong>Company:</strong> {{ employer_name }}</p>
                <p><strong>Address:</strong> {{ employer_address }}</p>
                <p><strong>Country:</strong> {{ employer_country }}</p>
            </div>
            <div class="party">
                <h4>EMPLOYEE</h4>
                <p><strong>Name:</strong> {{ worker_name }}</p>
                <p><strong>Address:</strong> {{ worker_address }}</p>
                <p><strong>Nationality:</strong> Romanian</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h3>JOB DETAILS</h3>
        <table>
            <tr><th>Position Title</th><td>{{ job_title }}</td></tr>
            <tr><th>Work Location</th><td>{{ work_location }}</td></tr>
            <tr><th>Job Description</th><td>{{ job_description }}</td></tr>
            <tr><th>Start Date</th><td>{{ start_date }}</td></tr>
            <tr><th>Contract Duration</th><td>{{ contract_duration }}</td></tr>
            <tr><th>Probationary Period</th><td>{{ probation_period }}</td></tr>
        </table>
    </div>

    <div class="section">
        <h3>WORKING CONDITIONS</h3>
        <table>
            <tr><th>Working Hours</th><td>{{ working_hours }}</td></tr>
            <tr><th>Salary</th><td>{{ salary }} {{ currency }}</td></tr>
            <tr><th>Annual Leave</th><td>{{ vacation_days }}</td></tr>
            <tr><th>Notice Period</th><td>{{ notice_period }}</td></tr>
        </table>
    </div>

    <div class="section">
        <h3>LEGAL FRAMEWORK</h3>
        <ul>
            <li>This contract is governed by the employment laws of {{ employer_country }}</li>
            <li>EU Regulation (EU) 2016/589 on free movement of workers applies</li>
            <li>Social security coordination under EU Regulation 883/2004</li>
            <li>Posted Workers Directive (EU) 2018/957 provisions apply if applicable</li>
        </ul>
    </div>

    <div class="section">
        <h3>WORKER RIGHTS</h3>
        <p>As an EU mobile worker, you have the right to:</p>
        <ul>
            <li>Equal treatment with national workers</li>
            <li>Social security benefits coordination</li>
            <li>Recognition of professional qualifications</li>
            <li>Family reunification under EU law</li>
            <li>Access to employment services and tax advantages</li>
        </ul>
    </div>

    <div class="section">
        <h3>DISPUTE RESOLUTION</h3>
        <p>Any disputes arising from this contract shall be resolved through:</p>
        <ol>
            <li>Direct negotiation between parties</li>
            <li>Mediation through competent labor authorities</li>
            <li>Jurisdiction of courts in {{ employer_country }}</li>
        </ol>
    </div>

    <div class="signature-section">
        <div class="signature">
            <p>___________________________</p>
            <p><strong>Employer Signature</strong></p>
            <p>Date: {{ current_date }}</p>
        </div>
        <div class="signature">
            <p>___________________________</p>
            <p><strong>Employee Signature</strong></p>
            <p>Date: {{ current_date }}</p>
        </div>
    </div>

    <div style="margin-top: 30px; font-size: 12px; color: #666;">
        <p><strong>Note:</strong> This contract template complies with EU employment law requirements.
        Local employment law of {{ employer_country }} may impose additional obligations.
        It is recommended to consult with local legal counsel before finalization.</p>
    </div>
</body>
</html>
"""
        return Template(template_content)

    def _get_data_sharing_template(self) -> Template:
        """Data sharing agreement template."""
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Data Sharing Agreement</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .section { margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>DATA SHARING AGREEMENT</h1>
        <h3>For EU Worker Placement Services</h3>
    </div>

    <div class="section">
        <h3>PARTIES</h3>
        <p><strong>Data Controller:</strong> {{ data_controller }}</p>
        <p><strong>Data Processor:</strong> {{ employer_name }}, {{ employer_country }}</p>
        <p><strong>Event:</strong> {{ event_name }} ({{ event_date }})</p>
        <p><strong>Date:</strong> {{ current_date }}</p>
    </div>

    <div class="section">
        <h3>PURPOSE</h3>
        <p>This agreement governs the sharing of Romanian worker data with {{ employer_name }}
        for the purpose of facilitating employment opportunities in the European Union.</p>
    </div>

    <div class="section">
        <h3>DATA CATEGORIES</h3>
        <ul>
            <li>Personal identification data (name, contact information)</li>
            <li>Professional experience and qualifications</li>
            <li>Skills and competencies</li>
            <li>Language abilities and certifications</li>
        </ul>
    </div>

    <div class="section">
        <h3>GDPR COMPLIANCE</h3>
        <p>Both parties commit to:</p>
        <ul>
            <li>Processing data only for specified employment purposes</li>
            <li>Implementing appropriate technical and organizational measures</li>
            <li>Ensuring data subject rights are respected</li>
            <li>Data retention for maximum {{ retention_period }} years</li>
            <li>Secure deletion of data when no longer needed</li>
        </ul>
    </div>

    <div class="section">
        <h3>SIGNATURES</h3>
        <p>Data Controller: ___________________________ Date: ___________</p>
        <p>Data Processor: ___________________________ Date: ___________</p>
    </div>
</body>
</html>
"""
        return Template(template_content)

    def _get_compliance_report_template(self) -> Template:
        """Compliance status report template."""
        template_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Compliance Status Report</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; }
        .summary { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }
        .category { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .verified { border-left: 4px solid green; }
        .pending { border-left: 4px solid orange; }
        .rejected { border-left: 4px solid red; }
        .progress-bar { background: #ddd; border-radius: 10px; overflow: hidden; height: 20px; margin: 10px 0; }
        .progress { background: #4caf50; height: 100%; transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="header">
        <h1>COMPLIANCE STATUS REPORT</h1>
        <h3>{{ event_name }}</h3>
        <p>Event Date: {{ event_date }}</p>
        <p>Report Generated: {{ report_date }}</p>
    </div>

    <div class="summary">
        <h3>Compliance Summary</h3>
        <div class="progress-bar">
            <div class="progress" style="width: {{ completion_percentage }}%;"></div>
        </div>
        <p><strong>Overall Completion: {{ completion_percentage }}%</strong></p>
        <p>Compliant Categories: {{ summary.compliant_categories }} / {{ summary.total_categories }}</p>
        <p>Status: {{ summary.status|title }}</p>
    </div>

    <div class="categories">
        <h3>Compliance Categories</h3>
        {% for category_name, category_data in categories.items() %}
        <div class="category {{ category_data.status }}">
            <h4>{{ category_name|replace('_', ' ')|title }}</h4>
            <p><strong>Status:</strong> {{ category_data.status|title }}</p>
            {% if category_data.verified_by %}
            <p><strong>Verified by:</strong> {{ category_data.verified_by }} on {{ category_data.verified_date }}</p>
            {% endif %}
            <ul>
            {% for requirement in category_data.requirements %}
                <li>{{ requirement }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""
        return Template(template_content)