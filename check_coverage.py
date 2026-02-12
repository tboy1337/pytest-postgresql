import json

with open('coverage.json') as f:
    data = json.load(f)

totals = data['totals']
print(f"Overall Coverage Metrics:")
print(f"  Line Coverage: {totals['percent_covered']:.2f}%")
print(f"  Branch Coverage: {totals['percent_branches_covered']:.2f}%")
print(f"  Covered/Total Statements: {totals['covered_lines']}/{totals['num_statements']}")
print(f"  Covered/Total Branches: {totals['covered_branches']}/{totals['num_branches']}")

# Calculate source-only coverage
source_files = {k: v for k, v in data['files'].items() if k.startswith('pytest_postgresql\\')}
source_covered = sum(f['summary']['covered_lines'] for f in source_files.values())
source_total = sum(f['summary']['num_statements'] for f in source_files.values())
source_branches_covered = sum(f['summary']['covered_branches'] for f in source_files.values())
source_branches_total = sum(f['summary']['num_branches'] for f in source_files.values())

print(f"\nSource Code Only (pytest_postgresql/*):")
print(f"  Line Coverage: {(source_covered/source_total*100):.2f}%")
print(f"  Branch Coverage: {(source_branches_covered/source_branches_total*100 if source_branches_total > 0 else 100):.2f}%")
print(f"  Covered/Total Statements: {source_covered}/{source_total}")
print(f"  Covered/Total Branches: {source_branches_covered}/{source_branches_total}")
