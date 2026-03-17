import { motion } from 'framer-motion'
import { AppMockup } from '@/components/AppMockup'
import { GitHubIcon, ShieldIcon, BotIcon } from '@/components/FeatureIcons'

/* ─── Animations ──────────────────────────────────────────────────────────── */

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: (i: number = 0) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.5, delay: i * 0.1 },
  }),
}


function Img({ src, alt = '', className }: { src: string; alt?: string; className?: string }) {
  const webp = src.replace(/\.png$/, '.webp')
  return (
    <picture>
      <source srcSet={webp} type="image/webp" />
      <img src={src} alt={alt} className={className} />
    </picture>
  )
}

/* ─── Data ────────────────────────────────────────────────────────────────── */

const features = [
  {
    icon: GitHubIcon,
    title: 'GitHub-native',
    desc: 'Your docs live in your repo. Push markdown, Mento renders it instantly — file tree, frontmatter, syntax highlighting, Mermaid diagrams.',
    img: '/illust-code.png',
  },
  {
    icon: ShieldIcon,
    title: 'Team access control',
    desc: 'Invite members by email. Each project has its own roles — admin, member, blocked. The project owner manages everything.',
    img: '/illust-access.png',
  },
  {
    icon: BotIcon,
    title: 'AI-ready via MCP',
    desc: 'One URL connects Claude AI to your documentation. Your team queries docs in natural language, gets answers with sources.',
    img: '/illust-startup.png',
  },
]

const steps = [
  { num: '01', title: 'Sign in', desc: 'Authenticate with your account in one click.' },
  { num: '02', title: 'Create a project', desc: 'Pick a GitHub repo. Name your project, choose your docs folder.' },
  { num: '03', title: 'Invite your team', desc: 'Add members by email. They get access instantly.' },
  { num: '04', title: 'Browse & query', desc: 'Read docs on the web — or connect Claude AI with one URL.' },
]

const useCases = [
  { title: 'Startups', desc: 'Ship internal docs without setting up a docs site. Your markdown is already there.', color: '#2a5a4a' },
  { title: 'Agencies', desc: 'One portal per client. Isolated access, custom domains, self-service.', color: '#4a8a6a' },
  { title: 'Open source', desc: 'Give contributors a clean docs experience directly from your repo.', color: '#c87941' },
]

/* ─── Page ────────────────────────────────────────────────────────────────── */

export default function WelcomePage() {
  return (
    <div className="min-h-screen bg-background overflow-x-hidden">
      {/* Hero — full-width image */}
      <section className="relative min-h-[90vh] flex items-center">
        {/* Background image */}
        <Img src="/illust-collab.png" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-r from-foreground/80 via-foreground/50 to-transparent" />

        {/* Nav overlaid */}
        <nav className="absolute top-0 left-0 right-0 z-20 max-w-6xl mx-auto flex justify-between items-center px-4 sm:px-8 py-4 sm:py-6">
          <a href="/" className="flex items-center gap-3">
            <img src="/logo-book.svg" alt="Mento" className="h-10 w-10 brightness-0 invert" />
            <span className="text-xl font-bold tracking-tight font-serif text-white">Mento</span>
          </a>
          <a
            href="/auth/login?next=/"
            className="text-sm font-medium bg-white/20 backdrop-blur text-white px-5 py-2.5 rounded-full hover:bg-white/30 transition border border-white/20"
          >
            Sign in
          </a>
        </nav>

        {/* Hero content */}
        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-8 py-20 sm:py-32">
          <motion.p
            variants={fadeUp} initial="hidden" animate="visible" custom={0}
            className="text-sm font-medium text-white/70 mb-4 tracking-wide uppercase"
          >
            Documentation portal
          </motion.p>
          <motion.h1
            variants={fadeUp} initial="hidden" animate="visible" custom={1}
            className="text-5xl md:text-6xl lg:text-7xl font-bold leading-[1.05] font-serif text-white max-w-2xl"
            style={{ letterSpacing: '-0.02em' }}
          >
            Your docs,
            <br />
            always accessible.
          </motion.h1>
          <motion.p
            variants={fadeUp} initial="hidden" animate="visible" custom={2}
            className="text-lg text-white/75 max-w-lg mt-6 leading-relaxed"
          >
            Mento turns your GitHub markdown into a clean, secure portal.
            Invite your team. Control access. Let AI read your docs too.
          </motion.p>
          <motion.div
            variants={fadeUp} initial="hidden" animate="visible" custom={3}
            className="flex gap-3 mt-8"
          >
            <a href="/auth/login?next=/" className="text-sm font-medium bg-white text-foreground px-7 py-3 rounded-full hover:bg-white/90 transition">
              Get started
            </a>
            <a href="#features" className="text-sm font-medium border border-white/30 text-white px-7 py-3 rounded-full hover:bg-white/10 transition">
              Learn more
            </a>
          </motion.div>
        </div>

        {/* Floating app mockup */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.5 }}
          className="absolute bottom-8 right-8 w-80 lg:w-96 z-10 hidden md:block"
        >
          <div className="shadow-2xl rounded-2xl overflow-hidden border border-white/20">
            <AppMockup />
          </div>
        </motion.div>
      </section>


      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-4 sm:px-8 py-24 md:py-32">
        <motion.p
          variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}
          className="text-sm font-medium text-muted-foreground mb-3 tracking-wide uppercase"
        >
          Features
        </motion.p>
        <motion.h2
          variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }} custom={1}
          className="text-3xl md:text-4xl font-bold mb-16 font-serif"
          style={{ letterSpacing: '-0.02em' }}
        >
          Everything you need,
          <br />
          nothing you don't.
        </motion.h2>

        <div className="space-y-8">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }} custom={i}
              className="grid md:grid-cols-[1fr_1.2fr] gap-8 p-8 rounded-2xl border border-foreground/[0.06] bg-card hover:shadow-sm transition-shadow"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-4">
                  <f.icon className="w-5 h-5" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{f.title}</h3>
                <p className="text-muted-foreground leading-relaxed">{f.desc}</p>
              </div>
              <div className="flex items-center">
                <Img src={f.img} alt={f.title} className="w-full h-40 rounded-xl object-cover" />
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Divider */}
      <div className="max-w-6xl mx-auto px-4 sm:px-8"><div className="h-px bg-foreground/[0.06]" /></div>

      {/* How it works */}
      <section className="max-w-6xl mx-auto px-4 sm:px-8 py-24 md:py-32">
        <motion.p
          variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}
          className="text-sm font-medium text-muted-foreground mb-3 tracking-wide uppercase"
        >
          How it works
        </motion.p>
        <motion.h2
          variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }} custom={1}
          className="text-3xl md:text-4xl font-bold mb-16 font-serif"
          style={{ letterSpacing: '-0.02em' }}
        >
          Four steps. Five minutes.
        </motion.h2>

        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-0">
          {steps.map((s, i) => (
            <motion.div
              key={s.num}
              variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }} custom={i}
              className="relative p-6 md:border-l border-b md:border-b-0 border-foreground/[0.06] first:border-l-0 last:border-b-0"
            >
              <span className="text-5xl font-bold text-primary/15 font-serif">{s.num}</span>
              <h3 className="font-semibold mt-2 mb-2">{s.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Divider */}
      <div className="max-w-6xl mx-auto px-4 sm:px-8"><div className="h-px bg-foreground/[0.06]" /></div>

      {/* Use cases */}
      <section className="max-w-6xl mx-auto px-4 sm:px-8 py-24 md:py-32">
        <motion.p
          variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}
          className="text-sm font-medium text-muted-foreground mb-3 tracking-wide uppercase"
        >
          Use cases
        </motion.p>
        <motion.h2
          variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }} custom={1}
          className="text-3xl md:text-4xl font-bold mb-16 font-serif"
          style={{ letterSpacing: '-0.02em' }}
        >
          Built for teams that ship.
        </motion.h2>

        <div className="grid md:grid-cols-3 gap-6">
          {useCases.map((uc, i) => (
            <motion.div
              key={uc.title}
              variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }} custom={i}
              className="group rounded-2xl border border-foreground/[0.06] bg-card p-8 hover:shadow-sm transition-all relative overflow-hidden"
            >
              {/* Color accent top bar */}
              <div className="absolute top-0 left-0 right-0 h-1 opacity-0 group-hover:opacity-100 transition-opacity" style={{ background: uc.color }} />
              <h3 className="text-lg font-semibold mb-3">{uc.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{uc.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-4 sm:px-8 py-16 md:py-24">
        <motion.div
          variants={fadeUp} initial="hidden" whileInView="visible" viewport={{ once: true }}
          className="relative rounded-3xl overflow-hidden"
        >
          {/* Background image */}
          <Img src="/illust-aerial.png" className="absolute inset-0 w-full h-full object-cover" />
          <div className="absolute inset-0 bg-foreground/60 backdrop-blur-[2px]" />
          <div className="relative rounded-3xl p-12 md:p-20 text-center">
            <h2 className="text-3xl md:text-5xl font-bold mb-4 font-serif text-white" style={{ letterSpacing: '-0.02em' }}>
              Ready to start?
            </h2>
            <p className="text-white/80 max-w-md mx-auto mb-8">
              Connect your GitHub repo, invite your team, and your docs are live in minutes.
            </p>
            <a
              href="/auth/login?next=/"
              className="inline-flex items-center text-sm font-medium bg-white text-foreground px-8 py-3.5 rounded-full hover:bg-white/90 transition"
            >
              Get started — it's free
            </a>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-4 sm:px-8 py-8 border-t border-foreground/[0.06]">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <img src="/logo-book.svg" alt="Mento" className="h-5 w-5" />
            <span className="text-sm font-medium tracking-tight font-serif">Mento</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <a href="/help" className="hover:text-foreground transition">Help</a>
            <a href="/legal" className="hover:text-foreground transition">Legal</a>
            <a href="/privacy" className="hover:text-foreground transition">Privacy</a>
            <a href="/terms" className="hover:text-foreground transition">Terms</a>
            <a href="https://github.com/AlexisLaporte/memento" className="hover:text-foreground transition" target="_blank">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
