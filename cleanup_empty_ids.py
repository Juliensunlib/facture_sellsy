#!/usr/bin/env python3
"""
Script de nettoyage pour identifier et supprimer les factures avec ID vide dans Airtable
"""

from airtable_api import AirtableAPI

def find_and_list_empty_id_invoices():
    """Trouve toutes les factures avec ID_Facture vide"""
    airtable = AirtableAPI()

    print("Recherche des factures avec ID vide...")

    try:
        formula = "OR({ID_Facture}='', {ID_Facture}=BLANK())"
        records = airtable.table.all(formula=formula)

        if not records:
            print("Aucune facture avec ID vide trouvée.")
            return []

        print(f"\n{len(records)} facture(s) avec ID vide trouvée(s):\n")

        for idx, record in enumerate(records, 1):
            fields = record.get('fields', {})
            record_id = record.get('id', 'N/A')

            print(f"{idx}. Record ID: {record_id}")
            print(f"   - Numéro: {fields.get('Numéro', 'N/A')}")
            print(f"   - Client: {fields.get('Client', 'N/A')}")
            print(f"   - Date: {fields.get('Date', 'N/A')}")
            print(f"   - Montant TTC: {fields.get('Montant_TTC', 'N/A')}")
            print(f"   - ID_Facture: '{fields.get('ID_Facture', 'N/A')}'")
            print()

        return records

    except Exception as e:
        print(f"Erreur lors de la recherche: {e}")
        return []

def delete_empty_id_invoices(records):
    """Supprime les factures avec ID vide"""
    if not records:
        print("Aucune facture à supprimer.")
        return

    airtable = AirtableAPI()

    print(f"\nSuppression de {len(records)} facture(s) avec ID vide...\n")

    for idx, record in enumerate(records, 1):
        record_id = record.get('id')
        fields = record.get('fields', {})
        numero = fields.get('Numéro', 'N/A')

        try:
            airtable.table.delete(record_id)
            print(f"{idx}/{len(records)} - Facture supprimée (Record ID: {record_id}, Numéro: {numero})")
        except Exception as e:
            print(f"{idx}/{len(records)} - Erreur lors de la suppression de {record_id}: {e}")

    print("\nSuppression terminée.")

if __name__ == "__main__":
    print("=" * 60)
    print("NETTOYAGE DES FACTURES AVEC ID VIDE DANS AIRTABLE")
    print("=" * 60)
    print()

    # Étape 1: Lister les factures problématiques
    empty_records = find_and_list_empty_id_invoices()

    # Étape 2: Demander confirmation avant suppression
    if empty_records:
        print("\n" + "=" * 60)
        response = input(f"\nVoulez-vous supprimer ces {len(empty_records)} facture(s) ? (oui/non): ")

        if response.lower() in ['oui', 'o', 'yes', 'y']:
            delete_empty_id_invoices(empty_records)
        else:
            print("Suppression annulée.")

    print("\n" + "=" * 60)
    print("Script terminé.")
    print("=" * 60)
