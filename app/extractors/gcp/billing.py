from typing import List, Dict, Any, Optional
from app.extractors.base import BaseExtractor, ExtractorMetadata
import logging

logger = logging.getLogger(__name__)


class GCPBillingExtractor(BaseExtractor):
    def get_metadata(self) -> ExtractorMetadata:
        return ExtractorMetadata(
            service_name="billing",
            version="1.0.0",
            description="Extracts GCP Billing accounts and associated resources",
            resource_types=[
                "gcp:billing:account",
                "gcp:billing:budget",
                "gcp:billing:project",
            ],
            cloud_provider="gcp",
            supports_regions=False,
            requires_pagination=False,
        )

    async def extract(
        self, region: Optional[str] = None, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        resources = []
        try:
            # Check if Billing API is enabled
            from app.cloud.gcp_api_check import is_gcp_api_enabled, API_SERVICE_MAP

            project_id = getattr(self.session, "project_id", None)
            if not project_id:
                raise ValueError("Project ID is required for Billing operations")

            api_service = API_SERVICE_MAP["billing"]
            if not is_gcp_api_enabled(
                project_id, api_service, getattr(self.session, "credentials", None)
            ):
                logger.warning(
                    f"GCP Billing API is not enabled for project {project_id}. Skipping extraction."
                )
                return []

            from google.cloud import billing
            from google.cloud.billing_budgets_v1 import BudgetServiceClient

            billing_client = billing.CloudBillingClient()
            budgets_client = BudgetServiceClient()

            try:
                # List Billing Accounts
                for account in billing_client.list_billing_accounts():
                    account_data = {
                        "name": account.name,
                        "type": "account",
                        "display_name": account.display_name,
                        "open": account.open,
                        "master_billing_account": account.master_billing_account,
                    }
                    resources.append(self.transform(account_data))

                    # List associated projects
                    try:
                        projects = billing_client.list_project_billing_info(
                            name=account.name
                        )
                        for project in projects:
                            project_data = {
                                "name": project.name,
                                "type": "project",
                                "project_id": project.project_id,
                                "billing_account_name": account.name,
                                "billing_enabled": project.billing_enabled,
                            }
                            resources.append(self.transform(project_data))
                    except Exception as e:
                        logger.warning(
                            f"Error listing billing projects for account {account.name}: {e}"
                        )

                    # List budgets for the account
                    try:
                        budgets = budgets_client.list_budgets(parent=account.name)
                        for budget in budgets:
                            budget_data = {
                                "name": budget.name,
                                "type": "budget",
                                "display_name": budget.display_name,
                                "budget_filter": (
                                    {
                                        "projects": list(budget.budget_filter.projects),
                                        "credit_types": list(
                                            budget.budget_filter.credit_types_treatment.credit_types
                                        ),
                                        "services": list(budget.budget_filter.services),
                                        "subaccounts": list(
                                            budget.budget_filter.subaccounts
                                        ),
                                        "labels": dict(budget.budget_filter.labels),
                                    }
                                    if budget.budget_filter
                                    else {}
                                ),
                                "amount": (
                                    {
                                        "specified_amount": {
                                            "currency_code": budget.amount.specified_amount.currency_code,
                                            "units": str(
                                                budget.amount.specified_amount.units
                                            ),
                                            "nanos": budget.amount.specified_amount.nanos,
                                        },
                                        "last_period_amount": budget.amount.last_period_amount,
                                    }
                                    if budget.amount
                                    else {}
                                ),
                                "threshold_rules": [
                                    {
                                        "threshold_percent": rule.threshold_percent,
                                        "spend_basis": rule.spend_basis,
                                    }
                                    for rule in budget.threshold_rules
                                ],
                                "notifications_rule": (
                                    {
                                        "pubsub_topic": budget.notifications_rule.pubsub_topic,
                                        "schema_version": budget.notifications_rule.schema_version,
                                    }
                                    if budget.notifications_rule
                                    else None
                                ),
                                "etag": budget.etag,
                            }
                            resources.append(self.transform(budget_data))
                    except Exception as e:
                        logger.warning(
                            f"Error listing budgets for account {account.name}: {e}"
                        )

            except Exception as e:
                logger.warning(f"Error listing Billing resources: {e}")

        except Exception as e:
            logger.error(f"Error extracting Billing resources: {e}")
        return resources

    def transform(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw Billing API response to standardized format"""
        resource_type_map = {
            "account": "gcp:billing:account",
            "budget": "gcp:billing:budget",
            "project": "gcp:billing:project",
        }

        base = {
            "service": "billing",
            "resource_type": resource_type_map[raw_data["type"]],
            "name": raw_data["name"].split("/")[-1],
            "id": raw_data["name"],
            "project_id": getattr(self.session, "project_id", "unknown"),
        }

        if raw_data["type"] == "account":
            base.update(
                {
                    "display_name": raw_data["display_name"],
                    "open": raw_data["open"],
                    "master_billing_account": raw_data["master_billing_account"],
                }
            )
        elif raw_data["type"] == "budget":
            base.update(
                {
                    "display_name": raw_data["display_name"],
                    "budget_filter": raw_data["budget_filter"],
                    "amount": raw_data["amount"],
                    "threshold_rules": raw_data["threshold_rules"],
                    "notifications_rule": raw_data["notifications_rule"],
                    "etag": raw_data["etag"],
                }
            )
        else:  # project
            base.update(
                {
                    "project_id": raw_data["project_id"],
                    "billing_account_name": raw_data["billing_account_name"].split("/")[
                        -1
                    ],
                    "billing_enabled": raw_data["billing_enabled"],
                }
            )

        return base
