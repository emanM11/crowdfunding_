
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

import { getHomepage } from "../api/core";
import CountUp from "../components/CountUp";
import ProjectCard from "../components/ProjectCard";
import Reveal from "../components/Reveal";
import HeroScene from "../components/HeroScene";

const urls = {
  "أجهزة-طبية": "M12 21v-8m4 4H8M9 3h6M12 3v6M20 12a8 8 0 11-16 0 8 8 0 0116 0z",
  "تعليم": "M12 3L2 8l10 5 10-5-10-5zm0 11L2 9m10 5l10-5m-10 5v6",
  "تقنية": "M9 3h6v2H9V3zm3 5h2v6h-2V8zM3 9h6v2H3V9zm12 0h6v2h-6V9zm-6 8h6v2H9v-2zm-6-4h6v2H3v-2zm12 0h6v2h-6v-2z",
  "بيئة": "M12 22v-7m0-3c-3-5-8-6-8-11 5 0 9 3 9 7M12 12c3-2 6-2 8-2 0 4-2 7-8 10",
  "مشروعات-صغيرة": "M3 7h18v13H3V7zm4 0V5a2 2 0 012-2h6a2 2 0 012 2v2M3 12h18M12 12v3",
  "مجتمع": "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2m8-13a4 4 0 100 8 4 4 0 000-8zm10 13v-2a4 4 0 00-3-3.87m-4 1.87a4 4 0 010-7.74",
  "فنون": "M4 20c4 1 8-1 10-3 2-2 6-8 6-12 0 0-4 0-9 4-3 2-6 5-7 8l-1 1a2 2 0 101 2zM9.5 10.5a2 2 0 11-4 0 2 2 0 014 0z",
  "قضايا-اجتماعية": "M20.8 4.6a5.5 5.5 0 00-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 00-7.8 7.8l1.1 1.1L12 21l7.7-7.5 1.1-1.1a5.5 5.5 0 000-7.8z",
};

function categoryIcon(slug) {
  const d = urls[slug] || urls["بيئة"];
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

function StatsBand({ stats }) {
  const raisedPiasters = Number(stats.total_raised) || 0;
  const raisedEgp = Math.round(raisedPiasters / 100);
  return (
    <div className="stats-band">
      <div className="container stats-grid">
        <div className="stat-item">
          <strong>
            <CountUp value={raisedEgp} /> EGP
          </strong>
          <span>Successfully Raised</span>
        </div>
        <div className="stat-item">
          <strong>
            <CountUp value={stats.projects} />
          </strong>
          <span>Published Projects</span>
        </div>
        <div className="stat-item">
          <strong>
            <CountUp value={stats.backers} />
          </strong>
          <span>Supporters</span>
        </div>
        <div className="stat-item">
          <strong>
            <CountUp value={stats.categories} />
          </strong>
          <span>Categories</span>
        </div>
      </div>
    </div>
  );
}

function ProjectScroller({ title, eyebrow, projects }) {
  if (!projects || projects.length === 0) return null;
  return (
    <Reveal className="container section">
      <div className="section-heading row">
        <h2>
          <span className="eyebrow">
            <Sparkles size={14} />
            {eyebrow}
          </span>
          {title}
        </h2>
        <Link to="/projects" className="btn btn-outline" style={{ marginBottom: 8 }}>
          View All
        </Link>
      </div>
      <motion.div
        className="project-scroller"
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, amount: 0.1 }}
        variants={{ show: { transition: { staggerChildren: 0.08 } } }}
      >
        {projects.map((p, i) => (
          <motion.div
            key={p.id}
            variants={{
              hidden: { opacity: 0, y: 26 },
              show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] } },
            }}
            className="card-motion"
            style={{ flex: "0 0 264px", scrollSnapAlign: "start" }}
          >
            <ProjectCard project={p} />
          </motion.div>
        ))}
      </motion.div>
    </Reveal>
  );
}

function SkeletonSections() {
  return (
    <div className="container section">
      <div className="skeleton-grid">
        {[1, 2, 3, 4].map((n) => (
          <div key={n} className="skeleton-card">
            <div className="skeleton sk-img" />
            <div className="sk-body">
              <div className="skeleton sk-line" />
              <div className="skeleton sk-line short" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(false);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    getHomepage()
      .then(({ data }) => setData(data))
      .catch(() => setLoadError(true));
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  const featured = data?.featured?.[0] || null;
  const featuredPct =
    featured &&
    Number(featured.total_target) > 0
      ? Math.min(100, Math.round((Number(featured.total_donations) / Number(featured.total_target)) * 100))
      : 0;

  return (
    <>
      <section className="hero">
        <div className="hero-orbs" aria-hidden="true">
          <span className="hero-orb o1" />
          <span className="hero-orb o2" />
          <span className="hero-orb o3" />
        </div>
        <div className="container hero-inner">
          <motion.div
            className="hero-copy"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            <motion.span
              className="hero-badge"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15, duration: 0.4 }}
            >
              An Egyptian Crowdfunding Platform
            </motion.span>
            <h1>Support an Idea, or Help Bring One to Life.</h1>
            <p>
              Takatof is a crowdfunding platform for real projects in Egypt — education, healthcare,
              and community initiatives led by people like you.
            </p>
            <form onSubmit={handleSearch} className="hero-actions">
              <div className="hero-search">
                <input
                  className="input"
                  placeholder="Search by project name or tag..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <button className="btn btn-primary" type="submit">
                  Search
                </button>
              </div>
              <Link to="/projects" className="btn btn-ghost">
                Explore Projects
              </Link>
            </form>
          </motion.div>
          {!loadError && (
            <motion.div
              className="hero-visual"
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.25, ease: [0.22, 1, 0.36, 1] }}
              aria-hidden="true"
            >
              <HeroScene featured={featured} featuredPct={featuredPct} />
            </motion.div>
          )}
        </div>
      </section>

      {loadError && (
        <div className="container section">
          <div className="form-alert">
            We couldn't load the homepage data right now. Please refresh the page.
          </div>
        </div>
      )}

      {!data && !loadError && <SkeletonSections />}

      {data && (
        <>
          {data.stats && <StatsBand stats={data.stats} />}

          <ProjectScroller title="Featured Projects" eyebrow="Worth Supporting" projects={data.featured} />
          <ProjectScroller title="Top-Rated Projects" eyebrow="Community Favorites" projects={data.top_rated} />
          <ProjectScroller title="Latest Projects" eyebrow="New on the Platform" projects={data.latest} />

          <Reveal className="container section">
            <h2 className="section-heading">
              Explore by Category
              <small> From agriculture to technology — there is a project for every interest.</small>
            </h2>
            {data.categories.length ? (
              <div className="category-grid stagger">
                {data.categories.map((c, i) => (
                  <Link key={c.id} to={`/categories/${c.slug}`} className="category-card">
                    <span
                      className="category-icon"
                      style={
                        i % 3 === 1
                          ? { background: "linear-gradient(135deg, var(--emerald-500), var(--emerald-700))", boxShadow: "0 8px 18px -8px rgba(5,150,105,.55)" }
                          : i % 3 === 2
                            ? { background: "var(--grad-cta)", boxShadow: "0 8px 18px -8px rgba(245,158,11,.55)" }
                            : undefined
                      }
                    >
                      {categoryIcon(c.slug)}
                    </span>
                    <span>
                      <span className="cc-name">{c.name}</span>
                      <br />
                      <span className="cc-slug">Browse /{c.slug}</span>
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="empty-state">No categories have been added yet.</p>
            )}
          </Reveal>

          <div className="container section">
            <Reveal className="dark-section">
              <div className="cta-band">
                <h2>Have an Idea Worth Bringing to Life?</h2>
                <p>Start your campaign today and build a community of supporters around your idea.</p>
                <div className="hero-actions">
                  <Link to="/projects/new" className="btn btn-primary">
                    Start Your Campaign
                  </Link>
                  <Link to="/projects" className="btn btn-ghost">
                    Explore First
                  </Link>
                </div>
              </div>
            </Reveal>
          </div>
        </>
      )}
    </>
  );
}

