import { useEffect } from "react"
import { ArrowDown, ArrowRight, BarChart3, BookOpen, Database, FileCheck2, Layers3, Search, ShieldCheck } from "lucide-react"
import { Link } from "react-router-dom"
import "./LandingPage.css"

const workflows = [
  { number: "01", title: "Discover", description: "Explore market activity, sectors and companies.", icon: Search },
  { number: "02", title: "Analyze", description: "Examine financial performance and business context.", icon: BarChart3 },
  { number: "03", title: "Verify", description: "Trace figures and conclusions back to their sources.", icon: ShieldCheck },
  { number: "04", title: "Organize", description: "Keep research structured and ready to revisit.", icon: BookOpen },
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
      { threshold: 0.14, rootMargin: "0px 0px -48px 0px" },
    )

    elements.forEach((element) => observer.observe(element))
    return () => observer.disconnect()
  }, [])
}

function Brand() {
  return (
    <Link className="landing-brand" to="/" aria-label="QRQuant home">
      <span className="landing-brand-mark" aria-hidden>Q</span>
      <span>QRQuant</span>
    </Link>
  )
}

function ProductPreview() {
  return (
    <div className="landing-preview" aria-label="Illustrative QRQuant research interface">
      <div className="preview-topbar">
        <span className="preview-window-dots" aria-hidden><i /><i /><i /></span>
        <span>QRQUANT / RESEARCH</span>
        <span className="preview-status"><span /> CONCEPT PREVIEW</span>
      </div>
      <div className="preview-layout">
        <aside className="preview-rail" aria-hidden>
          <span className="preview-rail-active"><Layers3 size={16} /></span>
          <span><BarChart3 size={16} /></span>
          <span><Database size={16} /></span>
          <span><FileCheck2 size={16} /></span>
        </aside>
        <div className="preview-main">
          <div className="preview-heading">
            <div><span className="preview-eyebrow">MARKET INTELLIGENCE</span><strong>Research overview</strong></div>
            <span className="preview-date">Illustrative interface</span>
          </div>
          <div className="preview-overview">
            <div className="preview-panel preview-market">
              <span className="preview-label">Market context</span>
              <div className="preview-chart" aria-hidden>
                <svg viewBox="0 0 520 128" role="presentation">
                  <defs><linearGradient id="preview-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#70b8b0" stopOpacity=".28"/><stop offset="100%" stopColor="#70b8b0" stopOpacity="0"/></linearGradient></defs>
                  <path d="M0 95 C28 90 38 70 66 76 S108 91 132 65 S174 76 199 52 S238 64 262 42 S301 55 328 31 S368 48 390 25 S430 36 454 16 S490 24 520 8 V128 H0Z" fill="url(#preview-fill)" />
                  <path d="M0 95 C28 90 38 70 66 76 S108 91 132 65 S174 76 199 52 S238 64 262 42 S301 55 328 31 S368 48 390 25 S430 36 454 16 S490 24 520 8" fill="none" stroke="#398b82" strokeWidth="2.5" />
                  <path d="M0 112 H520 M0 72 H520 M0 32 H520" stroke="#dce6e4" strokeDasharray="3 6" />
                </svg>
              </div>
              <div className="preview-axis"><span>Market history</span><span>Source-linked context</span></div>
            </div>
            <div className="preview-panel preview-sectors">
              <span className="preview-label">Research areas</span>
              {["Market overview", "Sector activity", "Company analysis", "Evidence records"].map((item, index) => (
                <div className="preview-list-row" key={item}><span className="preview-list-index">0{index + 1}</span><span>{item}</span><ArrowRight size={13} /></div>
              ))}
            </div>
          </div>
          <div className="preview-bottom">
            <div><span className="preview-label">Company research</span><strong>Financials · Valuation · Peers</strong></div>
            <div><span className="preview-label">Evidence trail</span><strong>Claim → Record → Source</strong></div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function LandingPage() {
  useScrollReveal()

  return (
    <main className="landing-page">
      <header className="landing-header">
        <div className="landing-header-inner">
          <Brand />
          <nav className="landing-nav" aria-label="Main navigation">
            <a href="#platform">Platform</a>
            <a href="#workflow">How it works</a>
            <a href="#methodology">Methodology</a>
          </nav>
          <Link className="landing-header-cta" to="/market-intelligence">Explore markets <ArrowRight size={15} /></Link>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-hero-glow" aria-hidden />
        <div className="landing-hero-grid" aria-hidden />
        <div className="landing-hero-inner">
          <div className="landing-hero-copy" data-reveal>
            <span className="landing-kicker"><span /> MARKET INTELLIGENCE · FINANCIAL RESEARCH · QUANTITATIVE TOOLS</span>
            <h1>Understand the markets. <em>Investigate the business.</em> Verify the numbers.</h1>
            <p>One connected platform for market context, company research and evidence-led quantitative analysis.</p>
            <div className="landing-hero-actions">
              <Link className="landing-button landing-button-primary" to="/market-intelligence">Explore QRQuant <ArrowRight size={17} /></Link>
              <a className="landing-button landing-button-secondary" href="#workflow">See how it works <ArrowDown size={16} /></a>
            </div>
            <span className="landing-hero-note">Explore market intelligence first. Sign in only when you need protected research tools.</span>
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
          <div className="landing-market-visual" data-reveal data-reveal-delay="100">
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

      <section className="landing-section landing-workflow-section" id="workflow">
        <div className="landing-section-inner">
          <div className="landing-section-heading" data-reveal>
            <span className="landing-section-kicker">02 / A CONNECTED WORKFLOW</span>
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
            <div className="evidence-node"><span>02</span><strong>Evidence & calculation</strong><small>What supports the result?</small></div>
            <div className="evidence-connector" />
            <div className="evidence-node evidence-source"><span>03</span><strong>Original source</strong><small>Where did it come from?</small></div>
          </div>
          <div className="landing-section-copy" data-reveal data-reveal-delay="100">
            <span className="landing-section-kicker">03 / EVIDENCE FIRST</span>
            <h2>Every number deserves a trail.</h2>
            <p>Distinguish reported facts from derived metrics and analytical interpretation. Keep reporting periods, timestamps, source records and data limitations visible.</p>
            <p className="landing-evidence-principle">Claim <span>→</span> Evidence <span>→</span> Source <span>→</span> Record <span>→</span> Point-in-time context</p>
          </div>
        </div>
      </section>

      <section className="landing-section landing-audience-section">
        <div className="landing-section-inner">
          <div className="landing-section-heading" data-reveal>
            <span className="landing-section-kicker">04 / ONE RESEARCH ENGINE</span>
            <h2>Useful at every level of research.</h2>
          </div>
          <div className="landing-audience-grid">
            <article className="landing-audience" data-reveal><span className="audience-icon"><Search size={20} /></span><h3>For individual users</h3><p>Build market understanding, investigate companies and organize your research with more context.</p></article>
            <article className="landing-audience" data-reveal data-reveal-delay="100"><span className="audience-icon"><Layers3 size={20} /></span><h3>For professional researchers</h3><p>Work with structured financial information, quantitative tools and traceable research outputs.</p></article>
          </div>
        </div>
      </section>

      <section className="landing-final-cta" data-reveal>
        <div className="landing-final-inner">
          <span className="landing-section-kicker">EXPLORE QRQUANT</span>
          <h2>Start with the market.<br />Go deeper with research.</h2>
          <p>Explore the platform and follow the questions worth investigating.</p>
          <Link className="landing-button landing-button-light" to="/market-intelligence">Explore markets <ArrowRight size={17} /></Link>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <Brand />
          <span>Market intelligence. Quantitative research. Evidence-led analysis.</span>
          <a href="#top" onClick={(event) => { event.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }) }}>Back to top ↑</a>
          <small>QRQuant is a research platform, not investment advice.</small>
        </div>
      </footer>
    </main>
  )
}
