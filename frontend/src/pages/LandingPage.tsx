import { useEffect, useRef, useState } from "react"
import {
  ArrowDown,
  ArrowRight,
  BarChart3,
  BookOpen,
  Building2,
  Database,
  FileCheck2,
  Layers3,
  Menu,
  Search,
  ShieldCheck,
  X,
} from "lucide-react"
import { Link } from "react-router-dom"
import "./LandingPage.css"

const workflows = [
  { number: "01", title: "Discover", description: "Start with market context, sector activity and the companies within the available research universe.", icon: Search },
  { number: "02", title: "Investigate", description: "Examine company information, financial periods, business context and observable market behaviour.", icon: BarChart3 },
  { number: "03", title: "Verify", description: "Separate reported facts from calculated metrics and trace research back to its supporting records.", icon: ShieldCheck },
  { number: "04", title: "Organize", description: "Keep the questions, comparisons and evidence behind your research connected.", icon: BookOpen },
]

const researchAreas = [
  {
    number: "01",
    title: "Market context",
    description: "Explore market structure, sector participation, movers and scheduled events before narrowing your research.",
    detail: "Begin with the wider market",
    icon: BarChart3,
    href: "/market-intelligence",
  },
  {
    number: "02",
    title: "Company investigation",
    description: "Move from a company overview into financial information, operating context, peers and event history.",
    detail: "Examine a business in context",
    icon: Building2,
    href: "/companies",
  },
  {
    number: "03",
    title: "Quantitative exploration",
    description: "Use observable fields and structured comparisons to explore patterns without turning them into buy or sell instructions.",
    detail: "Explore measurable conditions",
    icon: Layers3,
    href: "/screener",
  },
]

function useScrollReveal() {
  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>("[data-reveal]")
    if (!("IntersectionObserver" in window)) {
      elements.forEach((element) => element.classList.add("is-visible"))
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible")
            observer.unobserve(entry.target)
          }
        })
      },
      { threshold: 0.12, rootMargin: "0px 0px -36px 0px" },
    )

    elements.forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [])
}

function Brand() {
  return (
    <Link className="landing-brand" to="/" aria-label="QRQuant home">
      <span className="landing-brand-mark" aria-hidden="true">Q</span>
      <span>QRQuant</span>
    </Link>
  )
}

function ProductPreview() {
  return (
    <div className="landing-preview" role="img" aria-label="Illustrative QRQuant research interface, not live market data">
      <div className="preview-topbar">
        <span className="preview-window-dots" aria-hidden="true"><i /><i /><i /></span>
        <span>QRQUANT / RESEARCH WORKSPACE</span>
        <span className="preview-status"><span /> ILLUSTRATIVE PREVIEW</span>
      </div>
      <div className="preview-layout">
        <aside className="preview-rail" aria-hidden="true">
          <span className="preview-rail-active"><Layers3 size={16} /></span>
          <span><BarChart3 size={16} /></span>
          <span><Database size={16} /></span>
          <span><FileCheck2 size={16} /></span>
        </aside>
        <div className="preview-main">
          <div className="preview-heading">
            <div><span className="preview-eyebrow">MARKET INTELLIGENCE</span><strong>Research overview</strong></div>
            <span className="preview-date">Concept composition</span>
          </div>
          <div className="preview-context-row">
            <span><i /> Market context</span>
            <span>Coverage-aware research</span>
            <span>Source-linked records</span>
          </div>
          <div className="preview-overview">
            <div className="preview-panel preview-market">
              <span className="preview-label">Market history · illustrative</span>
              <div className="preview-chart" aria-hidden="true">
                <svg viewBox="0 0 520 128" role="presentation">
                  <defs><linearGradient id="preview-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#70b8b0" stopOpacity=".24"/><stop offset="100%" stopColor="#70b8b0" stopOpacity="0"/></linearGradient></defs>
                  <path d="M0 95 C28 90 38 70 66 76 S108 91 132 65 S174 76 199 52 S238 64 262 42 S301 55 328 31 S368 48 390 25 S430 36 454 16 S490 24 520 8 V128 H0Z" fill="url(#preview-fill)" />
                  <path d="M0 95 C28 90 38 70 66 76 S108 91 132 65 S174 76 199 52 S238 64 262 42 S301 55 328 31 S368 48 390 25 S430 36 454 16 S490 24 520 8" fill="none" stroke="#398b82" strokeWidth="2.5" />
                  <path d="M0 112 H520 M0 72 H520 M0 32 H520" stroke="#dce6e4" strokeDasharray="3 6" />
                </svg>
              </div>
              <div className="preview-axis"><span>Time-series view</span><span>No live values shown</span></div>
            </div>
            <div className="preview-panel preview-sectors">
              <span className="preview-label">Research pathways</span>
              {["Market overview", "Sector activity", "Company analysis", "Evidence records"].map((item, index) => (
                <div className="preview-list-row" key={item}><span className="preview-list-index">0{index + 1}</span><span>{item}</span><ArrowRight size={13} /></div>
              ))}
            </div>
          </div>
          <div className="preview-bottom">
            <div><span className="preview-label">Financial context</span><strong>Reported · Derived · Period</strong></div>
            <div><span className="preview-label">Evidence trail</span><strong>Claim → Record → Source</strong></div>
          </div>
        </div>
      </div>
      <div className="preview-disclaimer">Illustrative interface only. This preview does not display live prices or current market conditions.</div>
    </div>
  )
}

export default function LandingPage() {
  useScrollReveal()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const mobileMenuToggleRef = useRef<HTMLButtonElement | null>(null)

  function closeMobileMenu() {
    setMobileMenuOpen(false)
    mobileMenuToggleRef.current?.focus()
  }

  return (
    <main className="landing-page" id="top">
      <header className="landing-header">
        <div className="landing-header-inner">
          <Brand />
          <nav className={`landing-nav${mobileMenuOpen ? " is-open" : ""}`} aria-label="Main navigation">
            <a href="#platform" onClick={closeMobileMenu}>Platform</a>
            <a href="#workflow" onClick={closeMobileMenu}>How it works</a>
            <a href="#methodology" onClick={closeMobileMenu}>Methodology</a>
          </nav>
          <div className="landing-header-actions">
            <Link className="landing-header-cta" to="/market-intelligence">Explore markets <ArrowRight size={15} /></Link>
            <button className="landing-menu-toggle" type="button" aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"} aria-expanded={mobileMenuOpen} aria-controls="landing-mobile-navigation" ref={mobileMenuToggleRef} onClick={() => setMobileMenuOpen((open) => !open)}>
              {mobileMenuOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
          </div>
        </div>
        <nav id="landing-mobile-navigation" className={`landing-mobile-nav${mobileMenuOpen ? " is-open" : ""}`} aria-label="Mobile navigation" aria-hidden={!mobileMenuOpen} hidden={!mobileMenuOpen} onKeyDown={(event) => { if (event.key === "Escape") closeMobileMenu() }}>
          <a href="#platform" onClick={closeMobileMenu}>Platform <ArrowRight size={14} /></a>
          <a href="#workflow" onClick={closeMobileMenu}>How it works <ArrowRight size={14} /></a>
          <a href="#methodology" onClick={closeMobileMenu}>Methodology <ArrowRight size={14} /></a>
        </nav>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-glow" aria-hidden="true" />
        <div className="landing-hero-grid" aria-hidden="true" />
        <div className="landing-hero-inner">
          <div className="landing-hero-copy" data-reveal>
            <span className="landing-kicker"><span /> MARKET INTELLIGENCE <i /> FINANCIAL RESEARCH <i /> QUANTITATIVE TOOLS</span>
            <h1>Understand the markets. <em>Investigate the business.</em> Verify the numbers.</h1>
            <p>Research markets and companies in one connected workspace—where financial context, measurable observations and their supporting evidence stay connected.</p>
            <div className="landing-hero-actions">
              <Link className="landing-button landing-button-primary" to="/market-intelligence">Explore market intelligence <ArrowRight size={17} /></Link>
              <a className="landing-button landing-button-secondary" href="#workflow">See how it works <ArrowDown size={16} /></a>
            </div>
            <span className="landing-hero-note">Start exploring without an account. Research coverage and available data vary by instrument, metric and source.</span>
          </div>
          <div className="landing-hero-visual" data-reveal data-reveal-delay="120">
            <ProductPreview />
          </div>
        </div>
        <a className="landing-scroll-cue" href="#platform"><span /> Scroll to explore</a>
      </section>

      <section className="landing-section landing-market-section" id="platform">
        <div className="landing-section-inner landing-market-grid">
          <div className="landing-section-copy" data-reveal>
            <span className="landing-section-kicker">01 / START WITH THE MARKET</span>
            <h2>See the wider picture before you investigate the detail.</h2>
            <p>Explore market conditions, sector activity and scheduled events, then move naturally into the companies and questions that matter to your research.</p>
            <Link className="landing-text-link" to="/market-intelligence">Explore market intelligence <ArrowRight size={16} /></Link>
          </div>
          <div className="landing-market-visual" data-reveal data-reveal-delay="100" aria-label="Market research connects indices, sectors, events and companies">
            <div className="market-visual-orbit orbit-one" />
            <div className="market-visual-orbit orbit-two" />
            <div className="market-visual-core"><BarChart3 size={32} /><span>MARKETS</span></div>
            <div className="market-visual-label market-label-top">Market context</div>
            <div className="market-visual-label market-label-right">Sectors</div>
            <div className="market-visual-label market-label-bottom">Events</div>
            <div className="market-visual-label market-label-left">Companies</div>
          </div>
        </div>
      </section>

      <section className="landing-section landing-research-section">
        <div className="landing-section-inner">
          <div className="landing-section-heading" data-reveal>
            <span className="landing-section-kicker">02 / MOVE FROM CONTEXT TO DETAIL</span>
            <h2>One research journey. Different ways to investigate.</h2>
            <p>Choose a starting point, follow the evidence and keep the limits of the available data in view.</p>
          </div>
          <div className="landing-research-list">
            {researchAreas.map(({ number, title, description, detail, icon: Icon, href }) => (
              <article className="landing-research-row" data-reveal key={number}>
                <span className="research-number">{number}</span>
                <span className="research-icon"><Icon size={22} strokeWidth={1.7} /></span>
                <div className="research-copy"><h3>{title}</h3><p>{description}</p></div>
                <Link to={href} className="research-link" aria-label={detail}>{detail}<ArrowRight size={16} /></Link>
              </article>
            ))}
          </div>
          <p className="landing-coverage-note"><Database size={15} /> Coverage is not uniform. Availability depends on the instrument, company, reporting period, metric and source.</p>
        </div>
      </section>

      <section className="landing-section landing-workflow-section" id="workflow">
        <div className="landing-section-inner">
          <div className="landing-section-heading" data-reveal>
            <span className="landing-section-kicker">03 / A CONNECTED WORKFLOW</span>
            <h2>From discovery to research you can explain.</h2>
            <p>Move through each stage without losing the context behind your work.</p>
          </div>
          <div className="landing-workflow-list">
            {workflows.map(({ number, title, description, icon: Icon }, index) => (
              <article className="landing-workflow-item" data-reveal data-reveal-delay={String(index * 70)} key={number}>
                <span className="workflow-number">{number}</span>
                <span className="workflow-icon"><Icon size={21} strokeWidth={1.7} /></span>
                <div><h3>{title}</h3><p>{description}</p></div>
                <ArrowRight className="workflow-arrow" size={18} />
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-evidence-section" id="methodology">
        <div className="landing-section-inner landing-evidence-grid">
          <div className="landing-evidence-visual" data-reveal>
            <div className="evidence-node evidence-claim"><span>01</span><strong>Research claim</strong><small>What are we examining?</small></div>
            <div className="evidence-connector" />
            <div className="evidence-node"><span>02</span><strong>Metric & calculation</strong><small>What was reported or derived?</small></div>
            <div className="evidence-connector" />
            <div className="evidence-node"><span>03</span><strong>Evidence record</strong><small>Which observation supports it?</small></div>
            <div className="evidence-connector" />
            <div className="evidence-node evidence-source"><span>04</span><strong>Original source & time context</strong><small>Where did it come from, and when was it available?</small></div>
          </div>
          <div className="landing-section-copy" data-reveal data-reveal-delay="100">
            <span className="landing-section-kicker">04 / EVIDENCE FIRST</span>
            <h2>Every number deserves a trail.</h2>
            <p>Financial research needs more than a displayed value. It needs the reporting period, the calculation behind derived metrics, the source observation and the time context used to assess it.</p>
            <p className="landing-evidence-principle">Claim <span>→</span> Metric <span>→</span> Evidence <span>→</span> Source <span>→</span> Point-in-time context</p>
          </div>
        </div>
      </section>

      <section className="landing-section landing-audience-section">
        <div className="landing-section-inner">
          <div className="landing-section-heading" data-reveal>
            <span className="landing-section-kicker">05 / BUILT FOR CAREFUL RESEARCH</span>
            <h2>Useful for learning. Structured for deeper work.</h2>
          </div>
          <div className="landing-audience-grid">
            <article className="landing-audience" data-reveal><span className="audience-icon"><Search size={20} /></span><h3>For individual researchers</h3><p>Build market understanding, investigate businesses and learn to question the numbers behind a headline.</p></article>
            <article className="landing-audience" data-reveal data-reveal-delay="100"><span className="audience-icon"><Layers3 size={20} /></span><h3>For professional workflows</h3><p>Work with structured financial context, observable fields and research records that can be revisited and explained.</p></article>
          </div>
        </div>
      </section>

      <section className="landing-trust-section">
        <div className="landing-section-inner landing-trust-inner" data-reveal>
          <div><span className="landing-section-kicker">TRANSPARENT BY DESIGN</span><h2>Research context, not investment instructions.</h2></div>
          <p>QRQuant is a research and analytical workspace—not a broker, portfolio manager or source of personalized investment advice. Data can be delayed, incomplete or unavailable; always check the stated source, period and coverage before relying on a figure.</p>
        </div>
      </section>

      <section className="landing-final-cta" data-reveal>
        <div className="landing-final-inner">
          <span className="landing-section-kicker">EXPLORE QRQUANT</span>
          <h2>Start with the market.<br />Go deeper with research.</h2>
          <p>Explore the available market context, then follow the questions worth investigating.</p>
          <Link className="landing-button landing-button-light" to="/market-intelligence">Explore markets <ArrowRight size={17} /></Link>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <Brand />
          <span>Market intelligence. Financial research. Evidence-led analysis.</span>
          <a href="#top" onClick={(event) => { event.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }) }}>Back to top ↑</a>
          <small>QRQuant provides research tools and information, not investment advice. Coverage and data availability vary by source.</small>
        </div>
      </footer>
    </main>
  )
}
