from __future__ import annotations

import argparse
import re
import textwrap
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "terms": "http://purl.org/dc/terms/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
}


ANNOTATION_TAGS = {
    f"{{{NS['rdfs']}}}label": "label",
    f"{{{NS['rdfs']}}}comment": "comment",
    f"{{{NS['dc']}}}title": "title",
    f"{{{NS['dc']}}}description": "description",
    f"{{{NS['terms']}}}contributor": "contributor",
    f"{{{NS['terms']}}}license": "license",
    f"{{{NS['terms']}}}provenance": "provenance",
    f"{{{NS['skos']}}}prefLabel": "prefLabel",
    f"{{{NS['skos']}}}altLabel": "altLabel",
}


@dataclass
class Entity:
    iri: str
    kind: str
    labels: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    annotations: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    domains: list[str] = field(default_factory=list)
    ranges: list[str] = field(default_factory=list)
    subproperties: list[str] = field(default_factory=list)
    inverse_of: list[str] = field(default_factory=list)
    property_characteristics: list[str] = field(default_factory=list)
    superclasses: list[str] = field(default_factory=list)
    equivalent_classes: list[str] = field(default_factory=list)
    disjoint_with: list[str] = field(default_factory=list)
    restrictions: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    properties: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


def compact_iri(iri: str | None) -> str:
    if not iri:
        return ""
    if "#" in iri:
        return iri.rsplit("#", 1)[1]
    return iri.rstrip("/").rsplit("/", 1)[-1]


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def get_resource(element: ET.Element) -> str:
    return (
        element.attrib.get(f"{{{NS['rdf']}}}about")
        or element.attrib.get(f"{{{NS['rdf']}}}resource")
        or element.attrib.get(f"{{{NS['rdf']}}}ID")
        or element.attrib.get(f"{{{NS['rdf']}}}nodeID")
        or ""
    )


def iter_children_by_local(element: ET.Element, local_name: str) -> list[ET.Element]:
    suffix = "}" + local_name
    return [child for child in element if child.tag.endswith(suffix)]


def describe_restriction(element: ET.Element) -> str:
    on_props = [compact_iri(get_resource(child)) for child in iter_children_by_local(element, "onProperty")]
    on_prop = ", ".join(filter(None, on_props)) or "unknownProperty"

    parts: list[str] = []
    for child in element:
        local = child.tag.rsplit("}", 1)[-1]
        if local == "onProperty":
            continue
        resource = compact_iri(get_resource(child))
        text = clean_text(child.text)
        if resource:
            parts.append(f"{local} {resource}")
        elif text:
            parts.append(f"{local} {text}")
        elif len(child):
            nested = describe_restriction(child)
            if nested:
                parts.append(f"{local} ({nested})")
    detail = "; ".join(parts) if parts else "unspecified constraint"
    return f"{on_prop}: {detail}"


def parse_annotations(element: ET.Element, entity: Entity) -> None:
    for child in element:
        name = ANNOTATION_TAGS.get(child.tag)
        if not name:
            continue
        value = clean_text(child.text) or compact_iri(get_resource(child))
        if not value:
            continue
        entity.annotations[name].append(value)
        if name in {"label", "prefLabel"}:
            entity.labels.append(value)
        elif name in {"comment", "description"}:
            entity.comments.append(value)


def entity_from_element(element: ET.Element, kind: str) -> Entity:
    iri = get_resource(element)
    entity = Entity(iri=iri, kind=kind)
    parse_annotations(element, entity)
    return entity


def parse_ontology(root: ET.Element) -> tuple[dict[str, Entity], dict[str, str]]:
    entities: dict[str, Entity] = {}
    ontology_info: dict[str, str] = {}

    for ontology in root.findall("owl:Ontology", NS):
        ontology_info["iri"] = get_resource(ontology)
        for child in ontology:
            name = ANNOTATION_TAGS.get(child.tag)
            if name:
                value = clean_text(child.text) or compact_iri(get_resource(child))
                if value:
                    current = ontology_info.get(name, "")
                    ontology_info[name] = f"{current}; {value}" if current else value
            elif child.tag.endswith("}versionInfo"):
                ontology_info["versionInfo"] = clean_text(child.text)
            elif child.tag.endswith("}versionIRI"):
                ontology_info["versionIRI"] = get_resource(child)

    for tag, kind in [
        ("owl:Class", "Class"),
        ("owl:ObjectProperty", "ObjectProperty"),
        ("owl:DatatypeProperty", "DataProperty"),
        ("owl:AnnotationProperty", "AnnotationProperty"),
        ("owl:NamedIndividual", "Individual"),
    ]:
        for element in root.findall(tag, NS):
            entity = entity_from_element(element, kind)
            if entity.iri:
                entities[entity.iri] = entity

    for thing in root.findall("owl:Thing", NS):
        iri = get_resource(thing)
        type_iris = [get_resource(child) for child in iter_children_by_local(thing, "type")]
        if iri and any(type_iri.endswith("#NamedIndividual") for type_iri in type_iris):
            entity = entity_from_element(thing, "Individual")
            entity.types.extend(type_iri for type_iri in type_iris if not type_iri.endswith("#NamedIndividual"))
            entities[iri] = entity

    for element in root:
        iri = get_resource(element)
        if not iri or iri not in entities:
            continue
        entity = entities[iri]

        if entity.kind == "Class":
            for child in element:
                local = child.tag.rsplit("}", 1)[-1]
                resource = get_resource(child)
                if local == "subClassOf":
                    if resource:
                        entity.superclasses.append(resource)
                    for nested in child:
                        if nested.tag.endswith("}Restriction"):
                            entity.restrictions.append(describe_restriction(nested))
                elif local == "equivalentClass" and resource:
                    entity.equivalent_classes.append(resource)
                elif local == "disjointWith" and resource:
                    entity.disjoint_with.append(resource)

        if entity.kind in {"ObjectProperty", "DataProperty", "AnnotationProperty"}:
            for child in element:
                local = child.tag.rsplit("}", 1)[-1]
                resource = get_resource(child)
                if local == "domain" and resource:
                    entity.domains.append(resource)
                elif local == "range" and resource:
                    entity.ranges.append(resource)
                elif local == "subPropertyOf" and resource:
                    entity.subproperties.append(resource)
                elif local == "inverseOf" and resource:
                    entity.inverse_of.append(resource)
        if entity.kind == "Individual":
            for child in element:
                local = child.tag.rsplit("}", 1)[-1]
                resource = get_resource(child)
                text = clean_text(child.text)
                if local == "type":
                    if resource and not resource.endswith("#NamedIndividual"):
                        entity.types.append(resource)
                elif resource or text:
                    entity.properties[local].append(resource or text)

    # Some RDF/XML files type properties via rdf:type rather than tag names.
    for element in root:
        iri = get_resource(element)
        if not iri:
            continue
        for rdf_type in iter_children_by_local(element, "type"):
            type_iri = get_resource(rdf_type)
            if type_iri and iri in entities:
                if type_iri.endswith("#FunctionalProperty"):
                    entities[iri].property_characteristics.append("FunctionalProperty")
                elif type_iri.endswith("#InverseFunctionalProperty"):
                    entities[iri].property_characteristics.append("InverseFunctionalProperty")
                elif type_iri.endswith("#TransitiveProperty"):
                    entities[iri].property_characteristics.append("TransitiveProperty")
                elif type_iri.endswith("#SymmetricProperty"):
                    entities[iri].property_characteristics.append("SymmetricProperty")
                elif not type_iri.endswith("#NamedIndividual"):
                    entities[iri].types.append(type_iri)

    return entities, ontology_info


def sorted_entities(entities: dict[str, Entity], kind: str) -> list[Entity]:
    return sorted(
        [entity for entity in entities.values() if entity.kind == kind],
        key=lambda item: compact_iri(item.iri).lower(),
    )


def format_values(values: list[str], limit: int | None = None) -> str:
    compacted = list(dict.fromkeys(compact_iri(value) for value in values if value))
    if not compacted:
        return "-"
    if limit and len(compacted) > limit:
        shown = compacted[:limit]
        return ", ".join(shown) + f", ... (+{len(compacted) - limit})"
    return ", ".join(compacted)


def md_escape(value: str) -> str:
    return value.replace("|", "\\|")


def write_profile(entities: dict[str, Entity], ontology_info: dict[str, str], output: Path, language: str = "zh") -> None:
    classes = sorted_entities(entities, "Class")
    object_props = sorted_entities(entities, "ObjectProperty")
    data_props = sorted_entities(entities, "DataProperty")
    annotation_props = sorted_entities(entities, "AnnotationProperty")
    individuals = sorted_entities(entities, "Individual")

    lines: list[str] = []
    zh = language == "zh"
    heading = {
        "title": "本体概览" if zh else "Ontology Profile",
        "review_required": "需要人工审核" if zh else "Human Review Required",
        "review_note": (
            "本文件由 OWL 自动生成，用于后续标注前的人工审核。请重点检查缺失的 label/comment、容易混淆的类、"
            "对象属性的 domain/range 约束，以及抽取出的 restriction 是否符合你的本体语义。"
            if zh
            else "This profile is generated from an OWL file for human review before any downstream annotation. "
            "Check missing labels/comments, ambiguous classes, property domain/range constraints, and whether "
            "the extracted restrictions match the intended ontology semantics."
        ),
        "metadata": "本体元数据" if zh else "Ontology Metadata",
        "summary": "统计摘要" if zh else "Summary",
        "classes": "类" if zh else "Classes",
        "object_properties": "对象属性" if zh else "Object Properties",
        "data_properties": "数据属性" if zh else "Data Properties",
        "individuals": "已有实例" if zh else "Named Individuals",
        "annotation_properties": "注释属性" if zh else "Annotation Properties",
        "review_checklist": "审核清单" if zh else "Review Checklist",
    }

    lines.append(f"# {heading['title']}")
    lines.append("")
    lines.append(f"## {heading['review_required']}")
    lines.append("")
    lines.append(heading["review_note"])
    lines.append("")
    lines.append(f"## {heading['metadata']}")
    lines.append("")
    for key in ["iri", "versionIRI", "versionInfo", "title", "label", "description", "license", "contributor"]:
        if ontology_info.get(key):
            lines.append(f"- **{key}**: {ontology_info[key]}")
    lines.append("")
    lines.append(f"## {heading['summary']}")
    lines.append("")
    lines.append(f"- {'类' if zh else 'Classes'}: {len(classes)}")
    lines.append(f"- {'对象属性' if zh else 'Object properties'}: {len(object_props)}")
    lines.append(f"- {'数据属性' if zh else 'Data properties'}: {len(data_props)}")
    lines.append(f"- {'注释属性' if zh else 'Annotation properties'}: {len(annotation_props)}")
    lines.append(f"- {'已有实例' if zh else 'Named individuals'}: {len(individuals)}")
    lines.append("")

    lines.append(f"## {heading['classes']}")
    lines.append("")
    lines.append("| Class | Label | Superclasses | Restrictions | Comment |")
    lines.append("|---|---|---|---|---|")
    for entity in classes:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(compact_iri(entity.iri)),
                    md_escape("; ".join(entity.labels) or "-"),
                    md_escape(format_values(entity.superclasses, limit=6)),
                    md_escape("; ".join(entity.restrictions[:4]) + (f"; ... (+{len(entity.restrictions) - 4})" if len(entity.restrictions) > 4 else "") or "-"),
                    md_escape("; ".join(entity.comments[:2]) or "-"),
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append(f"## {heading['object_properties']}")
    lines.append("")
    lines.append("| Property | Label | Domain | Range | Superproperty | Inverse | Characteristics | Comment |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for entity in object_props:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(compact_iri(entity.iri)),
                    md_escape("; ".join(entity.labels) or "-"),
                    md_escape(format_values(entity.domains)),
                    md_escape(format_values(entity.ranges)),
                    md_escape(format_values(entity.subproperties)),
                    md_escape(format_values(entity.inverse_of)),
                    md_escape(", ".join(entity.property_characteristics) or "-"),
                    md_escape("; ".join(entity.comments[:2]) or "-"),
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append(f"## {heading['data_properties']}")
    lines.append("")
    if data_props:
        lines.append("| Property | Label | Domain | Range | Superproperty | Comment |")
        lines.append("|---|---|---|---|---|---|")
        for entity in data_props:
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(compact_iri(entity.iri)),
                        md_escape("; ".join(entity.labels) or "-"),
                        md_escape(format_values(entity.domains)),
                        md_escape(format_values(entity.ranges)),
                        md_escape(format_values(entity.subproperties)),
                        md_escape("; ".join(entity.comments[:2]) or "-"),
                    ]
                )
                + " |"
            )
    else:
        lines.append("未发现 `owl:DatatypeProperty` 声明。" if zh else "No `owl:DatatypeProperty` declarations were found.")
    lines.append("")

    lines.append(f"## {heading['individuals']}")
    lines.append("")
    if individuals:
        lines.append("| Individual | Types | Properties |")
        lines.append("|---|---|---|")
        for entity in individuals:
            props = []
            for prop, values in sorted(entity.properties.items()):
                props.append(f"{prop}: {format_values(values, limit=6)}")
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(compact_iri(entity.iri)),
                        md_escape(format_values(entity.types, limit=6)),
                        md_escape("; ".join(props) or "-"),
                    ]
                )
                + " |"
            )
    else:
        lines.append("未发现 `owl:NamedIndividual` 声明。" if zh else "No `owl:NamedIndividual` declarations were found.")
    lines.append("")

    lines.append(f"## {heading['annotation_properties']}")
    lines.append("")
    lines.append(", ".join(compact_iri(entity.iri) for entity in annotation_props) or "-")
    lines.append("")

    lines.append(f"## {heading['review_checklist']}")
    lines.append("")
    if zh:
        lines.append("- 确认重要类是否有可读的 label 和 comment。")
        lines.append("- 在作为标注约束前，确认对象属性的 domain/range 是否符合预期。")
        lines.append("- 标记不应直接参与标注的抽象类或分组类。")
        lines.append("- 补充源文档中可能出现的同义词、别名和表面形式。")
        lines.append("- 标记哪些关系必须有原文证据，不能只靠本体推理。")
        lines.append("- 决定低置信度候选应拒绝、暂缓，还是交给用户审核。")
    else:
        lines.append("- Confirm that important classes have readable labels and comments.")
        lines.append("- Confirm object property domain/range values before using them as annotation constraints.")
        lines.append("- Mark classes that should not be annotated directly because they are abstract grouping classes.")
        lines.append("- Add domain-specific synonyms or surface forms that appear in source documents.")
        lines.append("- Identify relations that require explicit evidence rather than inference.")
        lines.append("- Decide whether low-confidence candidates should be rejected, deferred, or sent to user review.")
    lines.append("")

    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a human-reviewable ontology profile from RDF/XML OWL.")
    parser.add_argument("owl_file", type=Path)
    parser.add_argument("--output", type=Path, default=Path("ontology_profile.md"))
    parser.add_argument("--language", choices=["zh", "en"], default="zh", help="Report language. Defaults to Chinese.")
    args = parser.parse_args()

    tree = ET.parse(args.owl_file)
    root = tree.getroot()
    entities, ontology_info = parse_ontology(root)
    write_profile(entities, ontology_info, args.output, language=args.language)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
