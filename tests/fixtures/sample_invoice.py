"""
Script pour créer des fichiers de test pour le Document Analyzer
"""
import pandas as pd
from pathlib import Path

# Créer une facture sample en Excel
def create_sample_invoice_excel():
    """Créer une facture sample au format Excel"""

    data = {
        'Description': [
            'Services de consultation',
            'Développement logiciel',
            'Formation équipe',
            '',
            'Sous-total',
            'TPS (5%)',
            'TVQ (9.975%)',
            'TOTAL'
        ],
        'Quantité': [10, 20, 5, '', '', '', '', ''],
        'Prix unitaire': [150, 200, 100, '', '', '', '', ''],
        'Montant': [1500, 4000, 500, '', 6000, 300, 598.50, 6898.50]
    }

    df = pd.DataFrame(data)

    output_path = Path(__file__).parent / "sample_invoice.xlsx"
    df.to_excel(output_path, index=False)
    print(f"✅ Facture créée: {output_path}")

    return output_path


def create_sample_data_extract():
    """Créer un fichier de données simple pour extraction"""

    data = {
        'Nom': ['Entreprise ABC Inc.', 'PME XYZ Ltée', 'Société 123'],
        'Revenu': [50000, 75000, 120000],
        'Dépenses': [30000, 45000, 80000],
        'Profit': [20000, 30000, 40000]
    }

    df = pd.DataFrame(data)

    output_path = Path(__file__).parent / "sample_data.xlsx"
    df.to_excel(output_path, index=False)
    print(f"✅ Données créées: {output_path}")

    return output_path


if __name__ == "__main__":
    create_sample_invoice_excel()
    create_sample_data_extract()
