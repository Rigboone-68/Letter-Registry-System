/**
 * The one generic placeholder every stub route in routes/index.jsx
 * renders (docs/architecture/frontend.md §19 — "placeholder protected
 * child routes only where necessary to establish the routing
 * architecture"). No feature logic of any kind — Phase 5A builds the
 * shell these screens will eventually live in, not the screens
 * themselves.
 */
export default function PlaceholderPage({ title, description }) {
  return (
    <section>
      <h1>{title}</h1>
      <p>{description ?? 'This screen is planned but not yet implemented.'}</p>
    </section>
  )
}
