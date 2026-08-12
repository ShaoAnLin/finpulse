import { useEffect, useRef, useState } from 'react'

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

function getFeaturedSnippet(article, intro, sections) {
  const sectionPreview = sections.find(({ content }) => content)?.content ?? ''
  return (article.snippet || intro || sectionPreview).trim()
}

function FeaturedCard({ article }) {
  const [expanded, setExpanded] = useState(false)
  const cardRef = useRef(null)
  const { intro, sections } = parseFeature(article.feature)
  const snippet = getFeaturedSnippet(article, intro, sections)

  useEffect(() => {
    if (!expanded) return undefined
    const handleClickOutside = (event) => {
      if (cardRef.current && !cardRef.current.contains(event.target)) {
        setExpanded(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('touchstart', handleClickOutside, { passive: true })
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('touchstart', handleClickOutside)
    }
  }, [expanded])

  const handleCardClick = (event) => {
    if (event.target.closest('a, button')) return
    setExpanded((value) => !value)
  }

  const handleCardKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setExpanded((value) => !value)
    }
  }

  return (
    <article
      className="group flex h-full cursor-pointer flex-col overflow-hidden rounded-2xl border border-blue-100 bg-gradient-to-br from-white via-white to-blue-50/70 p-4 shadow-[0_14px_40px_-24px_rgba(30,58,138,0.5)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_18px_45px_-24px_rgba(30,58,138,0.55)] sm:p-5"
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      ref={cardRef}
      tabIndex={0}
      aria-label={`${article.title}，${expanded ? '已展開完整內容' : '顯示摘要，按 Enter 或空白鍵可展開'}`}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <CategoryBadge category={article.category} />
        <span className="text-xs font-medium text-slate-500 sm:text-sm">{article.source}</span>
      </div>
      <h2 className="text-xl font-black leading-tight tracking-tight text-blue-950 sm:text-2xl">
        {article.title}
      </h2>
      {!expanded && (
        <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-700 sm:text-base">{snippet}</p>
      )}
      <div
        className={`grid transition-[grid-template-rows,opacity,margin] duration-300 ${
          expanded ? 'mt-4 grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
        }`}
        aria-hidden={!expanded}
      >
        <div className="overflow-hidden">
          <div className="space-y-3">
            {sections.filter(({ content }) => content).map(({ icon, content }, index) => {
              const details = featureSectionDetails[icon]
              return (
                <section className={`rounded-xl p-3 ${details.color}`} key={`${icon}-${index}`}>
                  <h3 className="text-sm font-bold sm:text-base">
                    <span aria-hidden="true">{icon}</span> {details.label}
                  </h3>
                  <p className="mt-1.5 whitespace-pre-line text-sm leading-6 opacity-90">{content}</p>
                </section>
              )
            })}
          </div>
          <div className="mt-3 flex justify-end">
            <button
              className="rounded-lg px-2 py-1 text-xs font-bold text-blue-900 transition hover:bg-blue-50"
              onClick={() => setExpanded(false)}
              type="button"
            >
              收合
            </button>
          </div>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3 border-t border-blue-100 pt-3">
        <span className="text-xs text-slate-500 sm:text-sm">來源：{article.source}</span>
        <a
          className="inline-flex items-center gap-1.5 rounded-lg bg-blue-900 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-blue-800 active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-900 sm:text-sm"
          href={article.link}
          onClick={(event) => event.stopPropagation()}
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

  const handleCardClick = (event) => {
    if (event.target.closest('a, button')) return
    setExpanded((value) => !value)
  }

  const handleCardKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setExpanded((value) => !value)
    }
  }

  return (
    <article
      className="cursor-pointer rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-300 hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-lg"
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      tabIndex={0}
      aria-label={`${article.title}，${expanded ? '已展開內容' : '按 Enter 或空白鍵可展開'}`}
    >
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
        aria-hidden={!expanded}
      >
        <div className="overflow-hidden">
          <p className="border-t border-slate-100 pt-4 text-sm leading-7 text-slate-700">
            {article.snippet}
          </p>
        </div>
      </div>
      <div className="mt-5 flex items-center justify-between gap-3">
        <a
          className="ml-auto text-sm font-bold text-teal-700 transition hover:text-teal-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700"
          href={article.link}
          onClick={(event) => event.stopPropagation()}
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
  const [activeTab, setActiveTab] = useState('today')
  const [news, setNews] = useState(null)
  const [error, setError] = useState('')
  const [history, setHistory] = useState(null)
  const [historyError, setHistoryError] = useState('')
  const [historyLoading, setHistoryLoading] = useState(false)

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
      })
      .catch(() => setError('今日新聞暫時無法載入，請稍後再試。'))
  }, [])

  useEffect(() => {
    if (activeTab !== 'history' || history || historyLoading || historyError) return

    setHistoryLoading(true)
    fetch('./news-history.json', { cache: 'no-store' })
      .then((response) => {
        if (!response.ok) throw new Error('無法取得歷史新聞')
        return response.json()
      })
      .then((data) => {
        if (!Array.isArray(data.days)) throw new Error('歷史新聞資料格式錯誤')
        setHistory(data)
      })
      .catch(() => setHistoryError('近 7 日焦點暫時無法載入，請稍後再試。'))
      .finally(() => setHistoryLoading(false))
  }, [activeTab, history, historyError, historyLoading])

  const dateLabel = news?.date
    ? new Intl.DateTimeFormat('zh-TW', { dateStyle: 'long' }).format(
        new Date(`${news.date}T00:00:00+08:00`),
      )
    : ''
  return (
    <main className="min-h-screen bg-slate-50 text-slate-800">
      <header className="relative overflow-hidden bg-gradient-to-br from-slate-950 via-blue-950 to-blue-900 text-white">
        <div aria-hidden="true" className="absolute -right-20 -top-28 h-64 w-64 rounded-full bg-teal-400/10 blur-3xl" />
        <div aria-hidden="true" className="absolute -bottom-28 left-1/3 h-56 w-56 rounded-full bg-amber-400/10 blur-3xl" />
        <div className="relative mx-auto max-w-6xl px-5 py-5 sm:px-8 sm:py-6">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber-400 sm:text-sm">
            FinPulse 財經脈動
          </p>
          <div className="mt-1.5 flex flex-col gap-1.5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h1 className="text-2xl font-black tracking-tight sm:text-3xl">
                {activeTab === 'today' ? 'FinPulse 今日焦點' : 'FinPulse 近 7 日焦點'}
              </h1>
              {activeTab === 'today' && dateLabel && (
                <p className="text-sm text-blue-100 sm:text-base">{dateLabel} 財經新聞摘要</p>
              )}
              {activeTab === 'history' && (
                <p className="text-sm text-blue-100 sm:text-base">回顧最近一週的 AI 整理焦點</p>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-5 py-6 sm:px-8 sm:py-8">
        <nav
          aria-label="新聞範圍"
          className="sticky top-3 z-10 mb-6 flex rounded-xl border border-slate-200 bg-white/95 p-1 shadow-lg backdrop-blur sm:static sm:mx-auto sm:w-fit"
        >
          {[
            ['today', '今日焦點'],
            ['history', '近 7 日回顧'],
          ].map(([value, label]) => (
            <button
              aria-current={activeTab === value ? 'page' : undefined}
              className={`flex-1 rounded-lg px-5 py-2.5 text-sm font-bold transition sm:flex-none ${
                activeTab === value
                  ? 'bg-blue-900 text-white shadow-sm'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-blue-950'
              }`}
              key={value}
              onClick={() => setActiveTab(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </nav>

        {activeTab === 'today' && !news && !error && (
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
        {activeTab === 'today' && error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-800 shadow-sm" role="alert">
            <p className="font-bold">新聞載入失敗</p>
            <p className="mt-1 text-sm">{error}</p>
          </div>
        )}
        {activeTab === 'today' && news && (
          <>
            <section aria-labelledby="featured-heading">
              <h2 className="sr-only" id="featured-heading">精選新聞</h2>
              {news.featured.length ? (
                <div className="grid gap-4 lg:grid-cols-2">
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

            <section className="mt-8 border-t border-slate-200 pt-5 sm:mt-10 sm:pt-6" aria-labelledby="candidate-heading">
              <div className="mt-1 flex items-end justify-between gap-4">
                <h2 id="candidate-heading" className="text-2xl font-black text-blue-950 sm:text-3xl">
                  更多即時新聞
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

        {activeTab === 'history' && historyLoading && (
          <div aria-label="載入近 7 日焦點中" className="space-y-6" role="status">
            {[0, 1].map((item) => (
              <div className="h-72 animate-pulse rounded-3xl bg-white shadow-sm" key={item} />
            ))}
            <span className="sr-only">載入近 7 日焦點中…</span>
          </div>
        )}
        {activeTab === 'history' && historyError && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-800 shadow-sm" role="alert">
            <p className="font-bold">歷史新聞載入失敗</p>
            <p className="mt-1 text-sm">{historyError}</p>
          </div>
        )}
        {activeTab === 'history' && history && !history.days.length && (
          <p className="rounded-2xl bg-white p-6 text-slate-600 shadow-sm">
            最近 7 日尚無 AI 整理焦點。
          </p>
        )}
        {activeTab === 'history' && history?.days.length > 0 && (
          <div className="space-y-10">
            {history.days.map((day) => {
              const historyDate = new Intl.DateTimeFormat('zh-TW', {
                dateStyle: 'long',
              }).format(new Date(`${day.date}T00:00:00+08:00`))
              return (
                <section aria-labelledby={`history-${day.date}`} key={day.date}>
                  <div className="mb-4 flex items-end justify-between gap-4">
                    <h2
                      className="text-2xl font-black text-blue-950 sm:text-3xl"
                      id={`history-${day.date}`}
                    >
                      {historyDate}
                    </h2>
                    <span className="text-sm text-slate-500">{day.featured.length} 則焦點</span>
                  </div>
                  <div className="grid gap-4 lg:grid-cols-2">
                    {day.featured.map((article) => (
                      <FeaturedCard key={article.link} article={article} />
                    ))}
                  </div>
                </section>
              )
            })}
          </div>
        )}
      </div>
    </main>
  )
}
