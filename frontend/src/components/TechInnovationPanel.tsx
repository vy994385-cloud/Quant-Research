/**
 * TECHNOLOGY — evidence-backed technology workspace.
 *
 * When evidence exists: grouped development lists (Technology / Innovation /
 * R&D / Future technology) with status tags. When it does not: one compact
 * coverage panel. No large UNKNOWN cards, no unsupported speculation.
 */

import type { CompanyResearch } from "../api/types"
import type { Intelligence, IntelligenceSection } from "../api/types"
import { formatLabel } from "../lib/format"
import { PanelHead, Tag } from "./ui"

type SectionKey = Exclude<keyof Intelligence, "unknown_missing">

interface GroupSpec {
  key: SectionKey
  title: string
}

const GROUPS: GroupSpec[] = [
  { key: "innovation", title: "Innovation & R&D" },
  { key: "future_technology", title: "Future technology" },
]

function GroupBlock({ spec, section }: { spec: GroupSpec; section: IntelligenceSection | null }) {
  const supported = Boolean(section && section.observations.length > 0)
  if (!supported) return null
  return (
    <article className="intel-block supported">
      <header className="intel-block-head">
        <h4>{spec.title}</h4>
        <Tag text={formatLabel(section!.status)} tone={section!.status === "SUPPORTED" ? "green" : "amber"} />
      </header>
      <ul className="intel-observations">
        {section!.observations.map((observation) => (
          <li key={observation}>{observation}</li>
        ))}
      </ul>
    </article>
  )
}

export default function TechInnovationPanel({ data }: { data: CompanyResearch }) {
  const blocks = GROUPS.map((group) => ({
    group,
    section: data.intelligence[group.key],
  }))
  const anySupported = blocks.some(
    (block) => block.section && block.section.observations.length > 0,
  )

  return (
    <div className="section-anchor" id="tech-innovation">
      <PanelHead
        title="Technology"
        subtitle="Technology and innovation activity recorded from evidence"
      />

      {anySupported ? (
        <div className="intel-blocks">
          {blocks.map((block) => (
            <GroupBlock key={block.group.key} spec={block.group} section={block.section} />
          ))}
        </div>
      ) : (
        <p className="limited-note tech-limited">
          Limited coverage — no technology or innovation activity is currently supported by
          recorded evidence for this company. Related developments may still appear in{" "}
          <a href="#company-events">Events</a>.
        </p>
      )}
    </div>
  )
}
