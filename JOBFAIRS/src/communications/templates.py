"""
Professional Email Templates for European Employer ANOFM Job Fair Integration.

Template management system that loads HTML content from external files
for better maintainability and easier editing of email templates.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, date

from config import get_config


class EmailTemplate(ABC):
    """
    Abstract base class for email templates.

    Provides common functionality for template processing, variable substitution,
    and HTML generation from external template files.
    """

    def __init__(self):
        """Initialize template with configuration and logging."""
        self.config = get_config()
        self.logger = logging.getLogger(self.__class__.__name__)

        # Set template directory relative to project root
        self.template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'templates')

    @abstractmethod
    def get_subject(self, **variables) -> str:
        """Get email subject with variable substitution."""
        pass

    @abstractmethod
    def get_html_template_file(self) -> str:
        """Get the filename of the HTML template."""
        pass

    @abstractmethod
    def get_text_content(self, **variables) -> str:
        """Get plain text content for email."""
        pass

    def load_html_template(self, filename: str) -> str:
        """
        Load HTML template from file.

        Args:
            filename: Template filename

        Returns:
            HTML template content
        """
        try:
            template_path = os.path.join(self.template_dir, filename)
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Template file not found: {template_path}")
            return self._get_fallback_html()
        except Exception as e:
            self.logger.error(f"Error loading template {filename}: {str(e)}")
            return self._get_fallback_html()

    def get_html_content(self, **variables) -> str:
        """Get HTML email content with variable substitution."""
        html_template = self.load_html_template(self.get_html_template_file())
        return self.substitute_variables(html_template, **variables)

    def _get_fallback_html(self) -> str:
        """Fallback HTML template when file loading fails."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Email Template</title>
        </head>
        <body>
            <h1>Email Template Error</h1>
            <p>Unable to load email template. Please contact support.</p>
        </body>
        </html>
        """

    def substitute_variables(self, content: str, **variables) -> str:
        """
        Substitute template variables in content.

        Args:
            content: Template content with {variable} placeholders
            **variables: Variables to substitute

        Returns:
            Content with variables substituted
        """
        try:
            # Add common variables
            common_vars = {
                'current_date': datetime.now().strftime('%B %d, %Y'),
                'current_year': datetime.now().year,
                'company_name': 'InterJob Romania',
                'privacy_url': self.config.gdpr.privacy_policy_url,
                'contact_email': self.config.email.brevo_sender_email
            }

            # Merge with provided variables
            all_variables = {**common_vars, **variables}

            # Substitute variables
            return content.format(**all_variables)

        except KeyError as e:
            self.logger.error(f"Missing template variable: {e}")
            return content
        except Exception as e:
            self.logger.error(f"Error substituting variables: {e}")
            return content


class GermanEmployerTemplate(EmailTemplate):
    """
    Email template for German automotive employers.

    Professional English communication highlighting:
    - Romanian worker quality and work ethic
    - EU mobility advantages
    - ANOFM job fair opportunities
    - Streamlined recruitment process
    """

    def get_subject(self, **variables) -> str:
        """Get subject line for German employers."""
        company_name = variables.get('company_name', 'your company')
        return f"Skilled Romanian Automotive Workers Available for {company_name}"

    def get_html_template_file(self) -> str:
        """Get the filename of the HTML template."""
        return "employer_opportunity_email.html"

    def get_text_content(self, **variables) -> str:
        """Get plain text content for German employers."""
        text_template = """
SKILLED ROMANIAN AUTOMOTIVE WORKERS AVAILABLE FOR {company_name}

Dear Hiring Manager,

We are reaching out regarding an excellent opportunity to connect your company with highly skilled Romanian automotive workers who are ready to contribute to Germany's automotive excellence.

WHY ROMANIAN AUTOMOTIVE WORKERS EXCEL IN GERMANY:
✓ Strong technical education and automotive expertise
✓ EU citizenship - no visa complications or delays
✓ Excellent German language skills and cultural adaptation
✓ Proven work ethic and commitment to quality standards
✓ Cost-effective recruitment with immediate availability

CURRENT WORKFORCE AVAILABILITY:
We are coordinating with Romanian ANOFM (National Employment Agency) job fairs in key industrial regions where skilled automotive workers are actively seeking opportunities in Germany.

AVAILABLE POSITIONS WE CAN FILL:
- Automotive Assembly: Production line workers, quality control
- Manufacturing Support: Machine operators, maintenance technicians
- Logistics & Warehousing: Forklift operators, inventory management
- Skilled Trades: Welders, electricians, mechanics

STREAMLINED PROCESS:
We handle all coordination with ANOFM job fairs, pre-screening candidates based on your specific requirements, and facilitate direct connections between you and qualified workers.

Would you be interested in learning more about how we can help {company_name} access this talented workforce? I would be happy to discuss your specific staffing needs and how our ANOFM connections can provide immediate solutions.

Best regards,
European Recruitment Team
InterJob Romania
Connecting talent across Europe

Apply at: https://interjob.ro/apply.html
Contact: {contact_email}

This message complies with EU employment mobility regulations and GDPR.
Privacy Policy: {privacy_url}
        """

        return self.substitute_variables(text_template, **variables)


class DutchEmployerTemplate(EmailTemplate):
    """
    Email template for Dutch agricultural employers.

    Professional English communication highlighting:
    - Romanian agricultural experience and skills
    - Seasonal and permanent employment options
    - EU mobility and legal compliance
    - ANOFM job fair recruitment pipeline
    """

    def get_subject(self, **variables) -> str:
        """Get subject line for Dutch employers."""
        company_name = variables.get('company_name', 'your operation')
        return f"Experienced Romanian Agricultural Workers for {company_name}"

    def get_html_template_file(self) -> str:
        """Get the filename of the HTML template."""
        return "employer_opportunity_email.html"  # Reuse same template

    def get_text_content(self, **variables) -> str:
        """Get plain text content for Dutch employers."""
        text_template = """
EXPERIENCED ROMANIAN AGRICULTURAL WORKERS FOR {company_name}

Dear Agricultural Manager,

We are writing to inform you about an excellent opportunity to connect your agricultural operation with highly experienced Romanian workers who are seeking employment opportunities in the Netherlands.

WHY ROMANIAN AGRICULTURAL WORKERS EXCEL IN THE NETHERLANDS:
✓ Extensive experience in modern agricultural techniques
✓ EU citizenship - immediate work authorization
✓ Strong work ethic and reliability in seasonal work
✓ Adaptability to Dutch agricultural practices
✓ Cost-effective solution for labor-intensive operations

CURRENT WORKFORCE AVAILABILITY:
We coordinate with Romanian ANOFM (National Employment Agency) job fairs where skilled agricultural workers are actively seeking opportunities in Dutch agriculture.

AGRICULTURAL SPECIALIZATIONS AVAILABLE:
- Greenhouse Operations: Vegetable cultivation, flower production
- Field Crops: Harvesting, planting, crop maintenance
- Livestock: Dairy farming, poultry, animal care
- Agricultural Support: Equipment operation, general farm work

STREAMLINED RECRUITMENT PROCESS:
We handle all coordination with ANOFM events, worker pre-screening based on your specific needs, and facilitate direct connections between your operation and qualified workers.

Would you be interested in learning more about how we can help {company_name} access this reliable agricultural workforce? I would be happy to discuss your seasonal or permanent staffing requirements.

Best regards,
European Agricultural Recruitment Team
InterJob Romania
Connecting agricultural talent across Europe

Apply at: https://interjob.ro/apply.html
Contact: {contact_email}

This message complies with EU agricultural employment regulations and GDPR.
Privacy Policy: {privacy_url}
        """

        return self.substitute_variables(text_template, **variables)


class ANOFMTemplate(EmailTemplate):
    """
    Email template for ANOFM events and officials.

    Professional Romanian communication highlighting:
    - European employer partnerships
    - Worker placement opportunities
    - ANOFM event participation
    - Mutual benefit and collaboration
    """

    def get_subject(self, **variables) -> str:
        """Get subject line for ANOFM events."""
        event_name = variables.get('event_name', 'evenimentul dvs.')
        return f"Parteneriat european pentru {event_name} - Oportunități de plasare în UE"

    def get_html_template_file(self) -> str:
        """Get the filename of the HTML template."""
        return "anofm_partnership_email.html"

    def get_text_content(self, **variables) -> str:
        """Get plain text content for ANOFM events."""
        text_template = """
PARTENERIAT EUROPEAN PENTRU {event_name} - OPORTUNITĂȚI DE PLASARE ÎN UE

Stimată echipă ANOFM,

Vă contactez în calitate de reprezentant al InterJob Romania pentru a discuta o oportunitate de colaborare în cadrul {event_name} din {event_location}, programat pentru {event_date}.

PARTENERIATUL NOSTRU EUROPEAN OFERĂ:
✓ Conectare directă cu angajatori din Germania și Olanda
✓ Oportunități în sectoarele automotive și agricol
✓ Procesare rapidă a documentelor UE
✓ Suport complet pentru mobilitatea europeană
✓ Urmărire post-plasare pentru succesul pe termen lung

ANGAJATORI EUROPENI ACTIVI:
Colaborăm în prezent cu companii din industria auto germană și operațiuni agricole olandeze care caută activ lucrători români calificați.

SECTOARE CU CERERE MARE:
- Automotive (Germania): Asamblare, control calitate, logistică
- Agricultură (Olanda): Sere, câmp, zootehnie, operațiuni de fermă
- Manufacturing: Operatori mașini, întreținere, producție
- Logistică: Depozitare, transport, management inventar

BENEFICII PENTRU PARTICIPANȚII LA {event_name}:
- Interviu direct cu reprezentanți ai angajatorilor europeni
- Informații detaliate despre condițiile de muncă și salarizare
- Asistență pentru documentația de mobilitate UE
- Suport pentru integrarea în țara de destinație

Ne-ar bucura să participăm la {event_name} și să contribuim la succesul evenimentului prin conectarea lucrătorilor români cu aceste oportunități europene de calitate.

Aș aprecia posibilitatea de a discuta detaliile acestui parteneriat și modalitățile prin care putem colabora cel mai eficient în cadrul evenimentului dvs.

Cu stimă,
Echipa de Parteneriate Europene
InterJob Romania
Mobilitate europeană pentru forța de muncă română

Informații suplimentare: https://interjob.ro/apply.html
Contact: {contact_email}

Această comunicare respectă reglementările europene pentru mobilitatea forței de muncă și GDPR.
Politica de confidențialitate: {privacy_url}
        """

        return self.substitute_variables(text_template, **variables)