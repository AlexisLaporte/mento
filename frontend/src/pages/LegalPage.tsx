import { Link } from 'react-router-dom'

function LegalNav() {
  return (
    <nav className="max-w-3xl mx-auto flex items-center justify-between px-4 sm:px-8 py-4">
      <Link to="/" className="flex items-center gap-2">
        <img src="/logo-book.svg" alt="Mento" className="h-7 w-7" />
        <span className="text-base font-bold tracking-tight font-serif">Mento</span>
      </Link>
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <Link to="/legal" className="hover:text-foreground transition">Legal</Link>
        <Link to="/privacy" className="hover:text-foreground transition">Privacy</Link>
        <Link to="/terms" className="hover:text-foreground transition">Terms</Link>
      </div>
    </nav>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8 bg-card rounded-xl border border-border p-6">
      <h2 className="text-base font-semibold mb-3">{title}</h2>
      <div className="text-sm text-muted-foreground leading-relaxed space-y-2">{children}</div>
    </section>
  )
}

export function LegalNoticePage() {
  return (
    <div className="min-h-screen bg-background">
      <LegalNav />
      <div className="max-w-3xl mx-auto px-4 sm:px-8 py-8">
        <h1 className="text-2xl font-bold font-serif mb-1">Mentions légales</h1>
        <p className="text-sm text-muted-foreground mb-8">Dernière mise à jour : mars 2026</p>

        <Section title="Éditeur">
          <p><strong className="text-foreground">Nom :</strong> Alexis Laporte</p>
          <p><strong className="text-foreground">Statut :</strong> Micro-entrepreneur</p>
          <p><strong className="text-foreground">SIREN :</strong> 817 607 237</p>
          <p><strong className="text-foreground">Contact :</strong> alexis@otomata.tech</p>
        </Section>

        <Section title="Hébergement">
          <p><strong className="text-foreground">Hébergeur :</strong> Scaleway SAS</p>
          <p><strong className="text-foreground">Adresse :</strong> 8 rue de la Ville l'Evêque, 75008 Paris, France</p>
          <p><strong className="text-foreground">Localisation :</strong> Paris, France</p>
        </Section>

        <Section title="Données personnelles">
          <p>
            Conformément au RGPD, vous disposez d'un droit d'accès, de rectification, de suppression
            et de portabilité de vos données. Pour exercer ces droits, contactez alexis@otomata.tech.
          </p>
          <p>
            Pour plus de détails, consultez notre <Link to="/privacy" className="text-primary hover:underline">politique de confidentialité</Link>.
          </p>
        </Section>
      </div>
    </div>
  )
}

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      <LegalNav />
      <div className="max-w-3xl mx-auto px-4 sm:px-8 py-8">
        <h1 className="text-2xl font-bold font-serif mb-1">Privacy policy</h1>
        <p className="text-sm text-muted-foreground mb-8">Last updated: March 2026</p>

        <Section title="What we collect">
          <p>When you sign in via Auth0, we store your <strong className="text-foreground">email address</strong>, <strong className="text-foreground">name</strong>, and <strong className="text-foreground">profile picture</strong> in your session.</p>
          <p>When you connect GitHub, we use an OAuth token (stored in session only) to list your installations and access repositories on your behalf.</p>
          <p>Project membership (email + role) is stored in our PostgreSQL database.</p>
        </Section>

        <Section title="What we don't collect">
          <p>No tracking pixels, no fingerprinting, no analytics cookies, no advertising. We don't sell or share your data with third parties for marketing purposes.</p>
        </Section>

        <Section title="Cookies">
          <p>We use a single <strong className="text-foreground">session cookie</strong> to keep you signed in. No other cookies are set.</p>
        </Section>

        <Section title="Third-party services">
          <ul className="list-none space-y-1.5">
            <li><strong className="text-foreground">Auth0</strong> (Okta) — authentication and identity management</li>
            <li><strong className="text-foreground">GitHub</strong> — repository access via GitHub App installation tokens</li>
            <li><strong className="text-foreground">Resend</strong> — transactional emails (invitations only)</li>
            <li><strong className="text-foreground">Scaleway</strong> — server hosting (Paris, France)</li>
          </ul>
        </Section>

        <Section title="Your GDPR rights">
          <p>You have the right to access, rectify, delete, and export your personal data. You can also object to processing or file a complaint with the CNIL.</p>
          <p>To exercise any of these rights, email <a href="mailto:alexis@otomata.tech" className="text-primary hover:underline">alexis@otomata.tech</a>.</p>
        </Section>

        <Section title="Data retention">
          <p>Session data is deleted when you sign out. Project membership data is retained as long as your account exists. You can request full deletion at any time.</p>
        </Section>
      </div>
    </div>
  )
}

export function TermsPage() {
  return (
    <div className="min-h-screen bg-background">
      <LegalNav />
      <div className="max-w-3xl mx-auto px-4 sm:px-8 py-8">
        <h1 className="text-2xl font-bold font-serif mb-1">Terms of use</h1>
        <p className="text-sm text-muted-foreground mb-8">Last updated: March 2026</p>

        <Section title="Purpose">
          <p>Mento (mento.cc) is a documentation portal that renders GitHub repository content with access control. These terms govern your use of the service.</p>
        </Section>

        <Section title="Account & access">
          <p>You sign in via Auth0 (Google or GitHub OAuth). You are responsible for the security of your account. Access to specific projects is managed by project owners through email-based invitations.</p>
        </Section>

        <Section title="Acceptable use">
          <p>You agree not to:</p>
          <ul className="list-disc pl-5 space-y-1 mt-1">
            <li>Use the service for illegal purposes</li>
            <li>Attempt to access projects you haven't been invited to</li>
            <li>Scrape, crawl, or automated mass-download content</li>
            <li>Interfere with the service's availability or security</li>
          </ul>
        </Section>

        <Section title="Content & intellectual property">
          <p>Documents displayed on Mento are sourced from GitHub repositories. The content belongs to the respective repository owners. Mento does not claim any rights over your content.</p>
          <p>The Mento platform (code, design, brand) is the property of Alexis Laporte.</p>
        </Section>

        <Section title="Limitation of liability">
          <p>Mento is provided "as is" without warranty. We are not liable for data loss, service interruptions, or any damages arising from the use of the platform. GitHub API availability is outside our control.</p>
        </Section>

        <Section title="Changes to terms">
          <p>We may update these terms at any time. Continued use of the service after changes constitutes acceptance. Material changes will be communicated via the application.</p>
        </Section>
      </div>
    </div>
  )
}
