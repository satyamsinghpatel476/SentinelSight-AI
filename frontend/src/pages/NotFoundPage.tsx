import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="page-section page-section--narrow" aria-labelledby="not-found-heading">
      <p className="eyebrow">404</p>
      <h1 id="not-found-heading">Page not found</h1>
      <p className="page-description">The requested SentinelSight AI page does not exist.</p>
      <Link className="button" to="/">
        Return to foundation
      </Link>
    </section>
  );
}
