from sellsy_api import get_recent_invoices
from airtable_api import find_invoice_by_id, create_invoice, update_invoice
import click

@click.group()
def cli():
    pass

@cli.command()
@click.option("--days", default=30, help="Nombre de jours à remonter")
def sync(days):
    print(f"🔄 Synchronisation des factures des {days} derniers jours...")
    invoices = get_recent_invoices(days)
    created, updated = 0, 0

    for invoice in invoices:
        invoice_id = str(invoice["id"])
        print(f"🔍 Recherche dans Airtable avec formule : {{ID_Facture}}='{invoice_id}'")
        airtable_record = find_invoice_by_id(invoice_id)

        if airtable_record is None:
            print(f"➕ Facture {invoice_id} non trouvée → création")
            create_invoice(invoice)
            created += 1
        else:
            existing = airtable_record["fields"]
            if (
                existing.get("Montant_HT") != invoice["montant_ht"]
                or existing.get("Montant_TTC") != invoice["montant_ttc"]
                or existing.get("Statut") != invoice["statut"]
            ):
                print(f"🔄 Facture {invoice_id} trouvée mais différente → mise à jour")
                update_invoice(airtable_record["id"], invoice)
                updated += 1
            else:
                print(f"✅ Facture {invoice_id} déjà à jour")

    print(f"✅ Synchronisation terminée. {created} créées, {updated} mises à jour.")
