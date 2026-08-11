import { useEffect, useId, useState } from 'react'

const categoryDetails = {
  international: {
    icon: '🌍',
    label: '國際焦點',
    badge: 'bg-teal-50 text-teal-800 ring-teal-200',
  },
  taiwan: {
    icon: '🇹🇼',
    label: '台灣焦點',
    badge: 'bg-amber-50 text-amber-800 ring-amber-200',
  },
}

function CategoryBadge({ category }) {
  const details = categoryDetails[category] ?? {
    icon: '📰',
    label: category || '財經',
    badge: 'bg-slate-100 text-slate-700 ring-slate-200',
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold ring-1 ring-inset ${details.badge}`}
    >
      {details.icon} {details.label}
    </span>
  )
}

const featureSectionDetails = {
  '📰': { label: '發生什麼事', color: 'bg-blue-50 text-blue-900' },
  '🔍': { label: '背景與脈絡', color: 'bg-amber-50 text-amber-950' },
  '🌐': { label: '市場影響', color: 'bg-teal-50 text-teal-950' },
}

function formatTimestamp(date) {
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function parseFeature(feature = '') {
  const markerPattern =
    /([📰🔍🌐])\s*(?:發生什麼事|背景與來龍去脈|背景與脈絡|影響)?[：:]?\s*/gu
  const matches = [...feature.matchAll(markerPattern)]

  if (!matches.length) {
    return { intro: '', sections: [{ icon: '📰', content: feature.trim() }] }
  }

  const intro = feature.slice(0, matches[0].index).trim()
  const sections = matches.map((match, index) => ({
    icon: match[1],
    content: feature
      .slice(
        match.index + match[0].length,
        matches[index + 1]?.index ?? feature.length,
      )
      .trim(),
  }))

  return { intro, sections }
}

function FeaturedCard({ article }) {
  const { intro, sections } = parseFeature(article.feature)

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-3xl border border-blue-100 bg-gradient-to-br from-white via-white to-blue-50/70 p-6 shadow-[0_18px_50px_-24px_rgba(30,58,138,0.45)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_24px_60px_-24px_rgba(30,58,138,0.55)] sm:p-8">
      <div className="mb-5 flex items-center justify-between gap-3">
        <CategoryBadge category={article.category} />
        <span className="text-sm font-medium text-slate-500">{article.source}</span>
      </div>
      <h2 className="text-2xl font-black leading-tight tracking-tight text-blue-950 sm:text-3xl">
        {article.title}
      </h2>
      <div className="mt-6 flex-1 space-y-4">
        {intro && <p className="text-base font-medium leading-7 text-slate-700">{intro}</p>}
        {sections.filter(({ content }) => content).map(({ icon, content }, index) => {
          const details = featureSectionDetails[icon]
          return (
            <section className={`rounded-2xl p-4 ${details.color}`} key={`${icon}-${index}`}>
              <h3 className="font-bold">
                <span aria-hidden="true">{icon}</span> {details.label}
              </h3>
              <p className="mt-2 whitespace-pre-line text-sm leading-7 opacity-90 sm:text-base">
                {content}
              </p>
            </section>
          )
        })}
      </div>
      <div className="mt-7 flex items-center justify-between gap-4 border-t border-blue-100 pt-5">
        <span className="text-sm text-slate-500">來源：{article.source}</span>
        <a
          className="inline-flex items-center gap-1.5 rounded-xl bg-blue-900 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-blue-800 active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-900"
          href={article.link}
          target="_blank"
          rel="noreferrer"
        >
          閱讀原文 <span aria-hidden="true">↗</span>
        </a>
      </div>
    </article>
  )
}

function CandidateCard({ article }) {
  const [expanded, setExpanded] = useState(false)
  const contentId = useId()

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-300 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-lg">
      <CategoryBadge category={article.category} />
      <h3 className="mt-3 text-lg font-bold leading-snug text-slate-900">
        {article.title}
      </h3>
      {!expanded && (
        <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-600">
          {article.snippet}
        </p>
      )}
      <div
        className={`grid transition-[grid-template-rows,opacity] duration-300 ${
          expanded ? 'mt-4 grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
        }`}
        id={contentId}
      >
        <div className="overflow-hidden">
          <p className="border-t border-slate-100 pt-4 text-sm leading-7 text-slate-700">
            {article.snippet}
          </p>
        </div>
      </div>
      <div className="mt-5 flex items-center justify-between gap-3">
        <button
          aria-controls={contentId}
          aria-expanded={expanded}
          className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-bold text-blue-800 transition hover:bg-blue-50 hover:text-blue-950 active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-800"
          onClick={() => setExpanded((value) => !value)}
          type="button"
        >
          {expanded ? '收合內容' : '展開內容'}
          <span
            aria-hidden="true"
            className={`transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
          >
            ▼
          </span>
        </button>
        <a
          className="text-sm font-bold text-teal-700 transition hover:text-teal-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
          href={article.link}
          target="_blank"
          rel="noreferrer"
        >
          原文 <span aria-hidden="true">↗</span>
        </a>
      </div>
      {expanded && (
        <div className="mt-5 flex items-center justify-between gap-3">
          <span className="text-sm text-slate-500">來源：{article.source}</span>
        </div>
      )}
    </article>
  )
}

export default function App() {
  const [news, setNews] = useState(null)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState(null)

  useEffect(() => {
    fetch('./news-today.json', { cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error('無法取得今日新聞')
        return response.json()
      })
      .then((data) => {
        if (!Array.isArray(data.featured) || !Array.isArray(data.candidates)) {
          throw new Error('新聞資料格式錯誤')
        }
        setNews(data)
        setLastUpdated(new Date())
      })
      .catch(() => setError('今日新聞暫時無法載入，請稍後再試。'))
  }, [])

  const dateLabel = news?.date
    ? new Intl.DateTimeFormat('zh-TW', { dateStyle: 'long' }).format(
        new Date(`${news.date}T00:00:00+08:00`),
      )
    : ''
  const updatedLabel = lastUpdated ? formatTimestamp(lastUpdated) : ''

  return (
    <main className="min-h-screen bg-slate-50 text-slate-800">
      <header className="relative overflow-hidden bg-gradient-to-br from-slate-950 via-blue-950 to-blue-900 text-white">
        <div aria-hidden="true" className="absolute -right-20 -top-32 h-80 w-80 rounded-full bg-teal-400/10 blur-3xl" />
        <div aria-hidden="true" className="absolute -bottom-36 left-1/3 h-72 w-72 rounded-full bg-amber-400/10 blur-3xl" />
        <div className="relative mx-auto max-w-6xl px-5 py-12 sm:px-8 sm:py-16">
          <p className="text-sm font-bold uppercase tracking-[0.22em] text-amber-400">
            FinPulse 財經脈動
          </p>
          <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-4xl font-black tracking-tight sm:text-5xl">
                FinPulse 今日焦點
              </h1>
              {dateLabel && <p className="mt-3 text-lg text-blue-100">{dateLabel} 財經新聞摘要</p>}
            </div>
            {updatedLabel && (
              <time
                className="text-sm font-medium text-blue-200"
                dateTime={lastUpdated.toISOString()}
              >
                最後更新於 {updatedLabel}
              </time>
            )}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8 sm:py-12">
        {!news && !error && (
          <div aria-label="載入今日新聞中" className="space-y-6" role="status">
            <div className="h-8 w-40 animate-pulse rounded-lg bg-slate-200" />
            <div className="grid gap-6 lg:grid-cols-2">
              {[0, 1].map((item) => (
                <div className="h-96 animate-pulse rounded-3xl bg-white shadow-sm" key={item} />
              ))}
            </div>
            <span className="sr-only">載入今日新聞中…</span>
          </div>
        )}
        {error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-800 shadow-sm" role="alert">
            <p className="font-bold">新聞載入失敗</p>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}
        {news && (
          <>
            <section aria-labelledby="featured-heading">
              <div className="mb-5">
                <p className="text-sm font-bold text-teal-700">LINE 同步精選</p>
                <h2 id="featured-heading" className="mt-1 text-3xl font-black text-blue-950">
                  今日焦點
                </h2>
              </div>
              {news.featured.length ? (
                <div className="grid gap-6 lg:grid-cols-2">
                  {news.featured.map((article) => (
                    <FeaturedCard key={article.link} article={article} />
                  ))}
                </div>
              ) : (
                <p className="rounded-2xl bg-white p-6 text-slate-600 shadow-sm">
                  今日焦點尚未更新。
                </p>
              )}
            </section>

            <section className="mt-14 border-t border-slate-200 pt-10" aria-labelledby="candidate-heading">
              <p className="text-sm font-bold text-amber-700">更多即時動態</p>
              <div className="mt-1 flex items-end justify-between gap-4">
                <h2 id="candidate-heading" className="text-3xl font-black text-blue-950">
                  候選新聞
                </h2>
                <span className="text-sm text-slate-500">{news.candidates.length} 則新聞</span>
              </div>
              {news.candidates.length ? (
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  {news.candidates.map((article) => (
                    <CandidateCard key={article.link} article={article} />
                  ))}
                </div>
              ) : (
                <p className="mt-5 rounded-2xl bg-white p-6 text-slate-600 shadow-sm">
                  今日暫無其他候選新聞。
                </p>
              )}
            </section>
          </>
        )}
      </div>
    </main>
  )
}
