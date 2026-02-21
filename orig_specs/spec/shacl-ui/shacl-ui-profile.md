# SemPKM SHACL UI Profile (v1)

SemPKM treats a subset of SHACL Core as UI-driving:
- sh:targetClass, sh:property, sh:path
- sh:name, sh:description, sh:message, sh:severity
- sh:minCount, sh:maxCount
- sh:datatype, sh:nodeKind, sh:class, sh:in
- sh:pattern and basic bounds
- sh:defaultValue
- sh:order
- sh:group / sh:PropertyGroup

Validation is async. Violations gate “conformance-required operations.” Warnings do not.