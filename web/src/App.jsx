import { useEffect, useState } from 'react'

const categoryDetails = {
  international: { icon: '🌍', label: '國際' },
  taiwan: { icon: '🇹🇼', label: '台灣' },
}

function CategoryBadge({ category }) {
  const details = categoryDetails[category] ?? { icon: '📰', label: category }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
      {details.icon} {details.label}
    </span>
  )
}

function FeaturedCard({ article }) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
      <div className="mb-5 flex items-center justify-between gap-3">
        <CategoryBadge category={article.category} />
        <span className="text-sm text-slate-500">{article.source}</span>
      </div>
      <h2 className="text-2xl font-bold leading-tight text-slate-950 sm:text-3xl">
        {article.title}
      </h2>
      <div className="mt-6 whitespace-pre-wrap text-base leading-8 text-slate-700">
        {article.feature}
      </div>
      <a
        className="mt-7 inline-flex font-semibold text-emerald-700 hover:text-emerald-900"
        href={article.link}
        target="_blank"
        rel="noreferrer"
      >
        閱讀原文 <span aria-hidden="true">↗</span>
      </a>
    </article>
  )
}

function CandidateCard({ article }) {
  return (
    <details className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <summary className="cursor-pointer list-none">
        <div className="flex items-start justify-between gap-4">
          <div>
            <CategoryBadge category={article.category} />
            <h3 className="mt-3 text-lg font-bold leading-snug text-slate-900">
              {article.title}
            </h3>
          </div>
          <span className="mt-1 shrink-0 rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700 group-open:hidden">
            展開
          </span>
          <span className="mt-1 hidden shrink-0 rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-600 group-open:inline">
            收合
          </span>
        </div>
        <p className="mt-3 line-clamp-2 text-sm leading-6 text-slate-600 group-open:hidden">
          {article.snippet}
        </p>
      </summary>
      <div className="mt-4 border-t border-slate-100 pt-4">
        <p className="text-base leading-7 text-slate-700">{article.snippet}</p>
        <div className="mt-5 flex items-center justify-between gap-3">
          <span className="text-sm text-slate-500">來源：{article.source}</span>
          <a
            className="font-semibold text-emerald-700 hover:text-emerald-900"
            href={article.link}
            target="_blank"
            rel="noreferrer"
          >
            閱讀原文 <span aria-hidden="true">↗</span>
          </a>
        </div>
      </div>
    </details>
  )
}

export default function App() {
  const [news, setNews] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('./news-today.json', { cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error('無法取得今日新聞')
        return response.json()
      })
      .then(setNews)
      .catch(() => setError('今日新聞暫時無法載入，請稍後再試。'))
  }, [])

  const dateLabel = news?.date
    ? new Intl.DateTimeFormat('zh-TW', { dateStyle: 'long' }).format(
        new Date(`${news.date}T00:00:00+08:00`),
      )
    : ''

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-slate-950 text-white">
        <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
          <p className="text-sm font-bold uppercase tracking-[0.22em] text-emerald-400">
            FinPulse 財經脈動
          </p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <h1 className="text-4xl font-black tracking-tight sm:text-5xl">今日熱門新聞</h1>
            {dateLabel && <time className="text-slate-300">{dateLabel}</time>}
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8 sm:py-12">
        {!news && !error && <p className="text-slate-500">載入今日新聞中…</p>}
        {error && <p className="rounded-2xl bg-white p-6 text-rose-700 shadow-sm">{error}</p>}
        {news && (
          <>
            <section aria-labelledby="featured-heading">
              <div className="mb-5">
                <p className="text-sm font-bold text-emerald-700">LINE 同步精選</p>
                <h2 id="featured-heading" className="mt-1 text-2xl font-black">
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

            <section className="mt-12" aria-labelledby="candidate-heading">
              <p className="text-sm font-bold text-emerald-700">更多即時動態</p>
              <h2 id="candidate-heading" className="mt-1 text-2xl font-black">
                候選新聞
              </h2>
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
