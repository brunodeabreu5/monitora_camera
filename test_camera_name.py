#!/usr/bin/env python3
"""
Script para testar nomes de câmera e detectar problemas.
"""

import re
import sys


def test_camera_name(name: str):
    """Testa se um nome de câmera tem problemas."""
    issues = []

    # Caracteres inválidos para nomes de arquivos
    invalid_chars = r'[<>:"|?*\\]'
    if re.search(invalid_chars, name):
        issues.append("X Contém caracteres inválidos para nomes de arquivos")

    # Caracteres problemáticos para Windows
    problematic_chars = ['/', '\\', ':']
    for char in problematic_chars:
        if char in name:
            issues.append(f"X Contém caractere problemático para Windows: '{char}'")

    # Nome muito longo (máximo 50 caracteres para nomes de arquivos)
    if len(name) > 50:
        issues.append(f"X Nome muito longo ({len(name)} caracteres)")

    # Nome muito curto
    if len(name) < 2:
        issues.append("X Nome muito curto")

    # Caracteres fora do padrão ASCII (ex: acentos)
    non_ascii = [c for c in name if ord(c) > 127]
    if non_ascii:
        issues.append(f"X Contém caracteres não-ASCII: {non_ascii}")

    return issues


def sanitize_camera_name(name: str) -> str:
    """Sanitiza um nome de câmera para remover problemas."""
    # Remove caracteres inválidos
    name = re.sub(r'[<>:"|?*\\]', '', name)
    # Remove espaços excessivos
    name = re.sub(r'\s+', '_', name)
    # Limita tamanho
    name = name[:50]
    return name


def main():
    print("=" * 60)
    print("Camera Name Test")
    print("=" * 60)

    # Testar diferentes nomes
    test_names = [
        ("Camera 1", "Default - OK"),
        ("Camera 2", "Default - OK"),
        ("Rua 1", "With space - OK"),
        ("Rua 1 Teste", "With space - OK"),
        ("Teste/Camera", "With / - PROBLEM"),
        ("Teste\\Camera", "With \\ - PROBLEM"),
        ("Teste:Camera", "With : - PROBLEM"),
        ("Teste*Camera", "With * - PROBLEM"),
        ("Teste?Camera", "With ? - PROBLEM"),
        ("Câmera 1", "With accent - PROBLEM"),
        ("Câmara 1", "With accent - PROBLEM"),
        ("Médico", "With accent - PROBLEM"),
        ("Camera 1 Teste Very Long Name That Might Cause Problems", "Too long - PROBLEM"),
        ("Rua 1 - Teste", "With hyphen - OK"),
        ("Rua1", "No spaces - OK"),
    ]

    print("\nTesting camera names:")
    print("-" * 60)

    problem_names = []
    ok_names = []

    for name, description in test_names:
        issues = test_camera_name(name)
        if issues:
            problem_names.append((name, description, issues))
            print(f"\n[!] {name} ({description}):")
            for issue in issues:
                print(f"      {issue}")
        else:
            ok_names.append(name)
            print(f"\n[OK] {name} ({description})")

    print("\n" + "=" * 60)
    print("Summary:")
    print("-" * 60)
    print(f"[OK] OK names: {len(ok_names)}")
    print(f"[!] Problem names: {len(problem_names)}")

    if problem_names:
        print("\nRecommended names:")
        for name in ok_names[:5]:
            print(f"  - {name}")
    else:
        print("\nAll tested names are OK!")

    print("\n" + "=" * 60)
    print("Name sanitization:")
    print("-" * 60)

    test_cases = [
        "Teste/Camera",
        "Teste\\Camera",
        "Teste:Camera",
        "Teste*Camera",
        "Teste?Camera",
        "Câmera 1",
        "Rua 1 Teste",
    ]

    for original in test_cases:
        sanitized = sanitize_camera_name(original)
        issues = test_camera_name(sanitized)
        if issues:
            print(f"X {original:20} -> {sanitized:20} [still has problems]")
        else:
            print(f"[OK] {original:20} -> {sanitized:20}")

    return 0


if __name__ == "__main__":
    sys.exit(main())