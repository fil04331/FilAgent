#!/usr/bin/env python3
"""
Script de validation du spec OpenAPI pour FilAgent
Vérifie la conformité syntaxique et sémantique du fichier openapi.yaml
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
import json

def load_openapi_spec(spec_path: Path) -> Tuple[Dict, List[str]]:
    """Charge et valide la syntaxe YAML du spec OpenAPI"""
    errors = []
    
    if not spec_path.exists():
        errors.append(f"❌ Fichier non trouvé: {spec_path}")
        return None, errors
    
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
        print(f"✅ Fichier YAML chargé: {spec_path}")
        return spec, errors
    except yaml.YAMLError as e:
        errors.append(f"❌ Erreur de syntaxe YAML: {e}")
        return None, errors

def validate_openapi_version(spec: Dict) -> List[str]:
    """Valide la version OpenAPI"""
    errors = []
    
    if 'openapi' not in spec:
        errors.append("❌ Champ 'openapi' manquant")
        return errors
    
    version = spec['openapi']
    if not version.startswith('3.'):
        errors.append(f"⚠️  Version OpenAPI non supportée: {version} (attendu: 3.x)")
    else:
        print(f"✅ Version OpenAPI: {version}")
    
    return errors

def validate_info(spec: Dict) -> List[str]:
    """Valide la section info"""
    errors = []
    
    if 'info' not in spec:
        errors.append("❌ Section 'info' manquante")
        return errors
    
    info = spec['info']
    required_fields = ['title', 'version']
    
    for field in required_fields:
        if field not in info:
            errors.append(f"❌ Champ 'info.{field}' manquant")
        else:
            print(f"✅ info.{field}: {info[field]}")
    
    # Vérifier la description détaillée (importante pour conformité)
    if 'description' not in info or len(info['description']) < 100:
        errors.append("⚠️  Description insuffisante (< 100 caractères)")
    else:
        print(f"✅ Description: {len(info['description'])} caractères")
    
    return errors

def validate_servers(spec: Dict) -> List[str]:
    """Valide la section servers"""
    errors = []
    
    if 'servers' not in spec:
        errors.append("⚠️  Section 'servers' manquante")
        return errors
    
    servers = spec['servers']
    if not isinstance(servers, list) or len(servers) == 0:
        errors.append("❌ Au moins un serveur requis")
        return errors
    
    for i, server in enumerate(servers):
        if 'url' not in server:
            errors.append(f"❌ Server[{i}]: 'url' manquant")
        else:
            print(f"✅ Server[{i}]: {server['url']}")
    
    return errors

def validate_paths(spec: Dict) -> List[str]:
    """Valide la section paths"""
    errors = []
    
    if 'paths' not in spec:
        errors.append("❌ Section 'paths' manquante")
        return errors
    
    paths = spec['paths']
    if not isinstance(paths, dict) or len(paths) == 0:
        errors.append("❌ Aucun endpoint défini")
        return errors
    
    print(f"✅ Endpoints définis: {len(paths)}")
    
    # Valider chaque endpoint
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            errors.append(f"❌ Path '{path}': format invalide")
            continue
        
        for method, operation in methods.items():
            if method.lower() not in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                continue
            
            # Vérifier opérationId (requis pour génération de code)
            if 'operationId' not in operation:
                errors.append(f"⚠️  {method.upper()} {path}: 'operationId' manquant")
            
            # Vérifier description (importante pour documentation)
            if 'description' not in operation:
                errors.append(f"⚠️  {method.upper()} {path}: 'description' manquante")
            
            # Vérifier responses
            if 'responses' not in operation:
                errors.append(f"❌ {method.upper()} {path}: 'responses' manquant")
            else:
                responses = operation['responses']
                if '200' not in responses and '201' not in responses:
                    errors.append(f"⚠️  {method.upper()} {path}: pas de réponse success définie")
    
    return errors

def validate_components(spec: Dict) -> List[str]:
    """Valide la section components/schemas"""
    errors = []
    
    if 'components' not in spec:
        errors.append("⚠️  Section 'components' manquante")
        return errors
    
    components = spec['components']
    
    if 'schemas' not in components:
        errors.append("⚠️  Section 'components/schemas' manquante")
        return errors
    
    schemas = components['schemas']
    print(f"✅ Schémas définis: {len(schemas)}")
    
    # Vérifier schémas critiques pour FilAgent
    critical_schemas = [
        'ChatRequest',
        'ChatResponse',
        'DecisionRecord',
        'ProvenanceGraph',
        'EventLog'
    ]
    
    for schema_name in critical_schemas:
        if schema_name not in schemas:
            errors.append(f"❌ Schéma critique manquant: {schema_name}")
        else:
            print(f"✅ Schéma critique: {schema_name}")
    
    return errors

def validate_compliance_metadata(spec: Dict) -> List[str]:
    """Valide les métadonnées de conformité spécifiques à FilAgent"""
    errors = []
    
    info = spec.get('info', {})
    description = info.get('description', '')
    
    # Vérifier mention des cadres de conformité
    compliance_frameworks = [
        'Loi 25',
        'RGPD',
        'AI Act',
        'NIST AI RMF'
    ]
    
    missing_frameworks = []
    for framework in compliance_frameworks:
        if framework not in description:
            missing_frameworks.append(framework)
    
    if missing_frameworks:
        errors.append(f"⚠️  Cadres de conformité non mentionnés: {', '.join(missing_frameworks)}")
    else:
        print(f"✅ Tous les cadres de conformité mentionnés")
    
    # Vérifier documentation des middlewares de conformité
    compliance_middlewares = [
        'EventLogger',
        'WormLogger',
        'DRManager',
        'ProvenanceTracker',
        'PIIRedactor',
        'ConstraintsEngine'
    ]
    
    missing_middlewares = []
    for middleware in compliance_middlewares:
        if middleware not in description:
            missing_middlewares.append(middleware)
    
    if missing_middlewares:
        errors.append(f"⚠️  Middlewares non documentés: {', '.join(missing_middlewares)}")
    else:
        print(f"✅ Tous les middlewares documentés")
    
    return errors

def validate_security(spec: Dict) -> List[str]:
    """Valide la configuration de sécurité"""
    errors = []
    
    # Vérifier si securitySchemes est défini
    if 'components' in spec and 'securitySchemes' in spec['components']:
        print("✅ Security schemes définis")
    else:
        errors.append("⚠️  Pas de 'securitySchemes' défini")
    
    # Vérifier si security est appliqué globalement
    if 'security' in spec:
        security = spec['security']
        if isinstance(security, list) and len(security) == 1 and security[0] == {}:
            print("⚠️  Sécurité désactivée (mode dev) - OK pour localhost")
        else:
            print("✅ Sécurité activée")
    else:
        errors.append("⚠️  Section 'security' manquante")
    
    return errors

def generate_report(all_errors: List[str]) -> bool:
    """Génère un rapport de validation"""
    print("\n" + "="*60)
    print("📊 RAPPORT DE VALIDATION OPENAPI")
    print("="*60)
    
    if not all_errors:
        print("\n✅ LE SPEC OPENAPI EST ENTIÈREMENT VALIDE !\n")
        return True
    else:
        print(f"\n❌ {len(all_errors)} problème(s) détecté(s):\n")
        for error in all_errors:
            print(f"  {error}")
        print("\n")
        return False

def main():
    """Fonction principale de validation"""
    print("🔍 Validation du spec OpenAPI FilAgent\n")
    
    # Déterminer le chemin du spec
    spec_path = Path(__file__).parent.parent / "openapi.yaml"
    
    if not spec_path.exists():
        # Essayer dans docs/api/
        spec_path = Path(__file__).parent.parent / "docs" / "api" / "openapi.yaml"
    
    if not spec_path.exists():
        # Essayer dans api/
        spec_path = Path(__file__).parent.parent / "api" / "openapi.yaml"
    
    print(f"📁 Chemin du spec: {spec_path}\n")
    
    # Charger le spec
    spec, errors = load_openapi_spec(spec_path)
    if spec is None:
        generate_report(errors)
        return 1
    
    # Valider chaque section
    all_errors = errors
    all_errors.extend(validate_openapi_version(spec))
    all_errors.extend(validate_info(spec))
    all_errors.extend(validate_servers(spec))
    all_errors.extend(validate_paths(spec))
    all_errors.extend(validate_components(spec))
    all_errors.extend(validate_compliance_metadata(spec))
    all_errors.extend(validate_security(spec))
    
    # Générer le rapport
    is_valid = generate_report(all_errors)
    
    # Optionnel : sauvegarder le rapport JSON
    report_path = Path(__file__).parent.parent / "validation_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "valid": is_valid,
            "spec_path": str(spec_path),
            "errors": all_errors,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }, f, indent=2)
    
    print(f"📄 Rapport détaillé sauvegardé: {report_path}\n")
    
    return 0 if is_valid else 1

if __name__ == "__main__":
    sys.exit(main())
