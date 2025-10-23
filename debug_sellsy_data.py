#!/usr/bin/env python3
"""
Script de debug pour analyser la structure des données Sellsy
"""

from sellsy_api import SellsyAPI
import json

def debug_recent_invoices():
    """Analyse les 10 dernières factures pour voir leur structure"""
    sellsy = SellsyAPI()

    print("=" * 80)
    print("DEBUG: ANALYSE DES FACTURES SELLSY")
    print("=" * 80)
    print()

    print("Récupération des 10 dernières factures...")
    invoices = sellsy.get_all_invoices(limit=10)

    if not invoices:
        print("Aucune facture trouvée.")
        return

    print(f"\n{len(invoices)} facture(s) récupérée(s).\n")
    print("=" * 80)

    for idx, invoice in enumerate(invoices, 1):
        print(f"\nFACTURE #{idx}")
        print("-" * 80)

        # Afficher les clés principales
        print(f"Clés disponibles: {list(invoice.keys())}")

        # Vérifier la présence de l'ID
        invoice_id = invoice.get("id")
        print(f"\nID présent: {invoice_id is not None}")
        print(f"Valeur de l'ID: {invoice_id}")
        print(f"Type de l'ID: {type(invoice_id)}")

        # Afficher d'autres champs importants
        print(f"\nNuméro/Référence:")
        for key in ["reference", "number", "decimal_number"]:
            if key in invoice:
                print(f"  - {key}: {invoice[key]}")

        print(f"\nDate:")
        for key in ["created_at", "date", "created"]:
            if key in invoice:
                print(f"  - {key}: {invoice[key]}")

        # Afficher les montants
        print(f"\nMontants:")
        if "amounts" in invoice:
            print(f"  Structure amounts: {list(invoice['amounts'].keys())}")
            for key in ["total_excluding_tax", "total_including_tax"]:
                if key in invoice["amounts"]:
                    print(f"  - {key}: {invoice['amounts'][key]}")

        # Afficher les informations client
        print(f"\nClient:")
        if "relation" in invoice:
            print(f"  Structure relation: {list(invoice['relation'].keys())}")
            print(f"  - Nom: {invoice['relation'].get('name')}")
            print(f"  - ID: {invoice['relation'].get('id')}")

        # Afficher le statut
        print(f"\nStatut: {invoice.get('status', 'N/A')}")

        # Afficher la structure complète (premier niveau uniquement)
        print(f"\nStructure complète (premier niveau):")
        for key, value in invoice.items():
            value_type = type(value).__name__
            if isinstance(value, (dict, list)):
                print(f"  - {key}: <{value_type}>")
            else:
                print(f"  - {key}: {value} ({value_type})")

        print("\n" + "=" * 80)

    # Tester la récupération des détails d'une facture
    if invoices:
        first_invoice_id = invoices[0].get("id")
        if first_invoice_id:
            print(f"\n\nTEST: Récupération des détails de la facture {first_invoice_id}")
            print("-" * 80)
            details = sellsy.get_invoice_details(first_invoice_id)

            if details:
                print("Détails récupérés avec succès!")
                print(f"Clés dans les détails: {list(details.keys())}")
                print(f"ID dans les détails: {details.get('id')}")
            else:
                print("Impossible de récupérer les détails")
        else:
            print("\nATTENTION: La première facture n'a pas d'ID!")

if __name__ == "__main__":
    try:
        debug_recent_invoices()
    except Exception as e:
        print(f"\n\nERREUR: {e}")
        import traceback
        traceback.print_exc()
