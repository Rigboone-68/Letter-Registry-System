import EmptyState from './EmptyState'
import ErrorState from './ErrorState'
import LoadingState from './LoadingState'
import styles from './CorrespondenceTrendChart.module.css'

const CHART_WIDTH = 600
const CHART_HEIGHT = 180
const TOP_PADDING = 12
const BOTTOM_PADDING = 12

function scaleY(count, maxCount) {
  const usableHeight = CHART_HEIGHT - TOP_PADDING - BOTTOM_PADDING
  return CHART_HEIGHT - BOTTOM_PADDING - (count / maxCount) * usableHeight
}

function pointsToCoordinates(points, key, maxCount) {
  return points.map((point, index) => {
    const x = points.length === 1 ? CHART_WIDTH / 2 : (index / (points.length - 1)) * CHART_WIDTH
    return { x, y: scaleY(point[key], maxCount) }
  })
}

function toPolylineAttr(coordinates) {
  return coordinates.map(({ x, y }) => `${x},${y}`).join(' ')
}

const MAX_AXIS_TICKS = 6

/**
 * Picks which points get an x-axis label. Showing every point's label
 * for a long series would overlap into an unreadable smear, so once
 * there are more than `MAX_AXIS_TICKS` points this thins them to an
 * evenly-spaced subset (always including the first and last) — never
 * silently dropping to just the two endpoints, which would leave every
 * month in between unlabeled on the graphic (the exact gap this fixes:
 * with only 1-2 months of data every month already showed; a third
 * month would have made the middle one invisible).
 */
function selectAxisTicks(points) {
  if (points.length <= MAX_AXIS_TICKS) {
    return points.map((point, index) => ({ point, index }))
  }
  const step = (points.length - 1) / (MAX_AXIS_TICKS - 1)
  const indices = new Set()
  for (let tick = 0; tick < MAX_AXIS_TICKS; tick += 1) {
    indices.add(Math.round(tick * step))
  }
  return Array.from(indices)
    .sort((a, b) => a - b)
    .map((index) => ({ point: points[index], index }))
}

/**
 * Correspondence Activity Over Time (Phase 6D,
 * docs/architecture/dashboard.md "Phase 6D" section) — a two-series
 * line chart (Incoming vs Outgoing) built from `mergeTrendSeries`
 * (`utils/aggregateChartHelpers.js`), which itself combines two
 * bounded, direction-filtered `group_by=month` requests — never a
 * two-dimensional backend aggregate (the Phase 6C API deliberately
 * has none) and never a client-side pass over raw Letters.
 *
 * The SVG plot is purely decorative (`aria-hidden`) — every value it
 * draws is also present as real, always-visible text in the legend
 * and the "View exact monthly counts" table below it, so nothing here
 * depends on a tooltip or a rendered pixel to be understood. The two
 * series are distinguished by more than color alone: a solid vs.
 * dashed line, and a circle vs. square marker, each also named in the
 * legend's own text.
 */
export default function CorrespondenceTrendChart({ points, loading, error, emptyMessage }) {
  if (loading) return <LoadingState label="Loading correspondence activity..." />
  if (error) return <ErrorState message={error.message} />
  if (!points || points.length === 0) return <EmptyState message={emptyMessage} />

  const maxCount = Math.max(...points.map((point) => Math.max(point.incoming, point.outgoing)), 1)
  const incomingCoordinates = pointsToCoordinates(points, 'incoming', maxCount)
  const outgoingCoordinates = pointsToCoordinates(points, 'outgoing', maxCount)

  return (
    <div className={styles.root}>
      <p className={styles.description}>
        Monthly Incoming vs. Outgoing correspondence volume.
      </p>

      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <svg className={styles.legendSwatch} viewBox="0 0 24 12" aria-hidden="true">
            <line x1="0" y1="6" x2="24" y2="6" className={styles.incomingLine} />
            <circle cx="12" cy="6" r="3" className={styles.incomingMarker} />
          </svg>
          Incoming / Diary
        </span>
        <span className={styles.legendItem}>
          <svg className={styles.legendSwatch} viewBox="0 0 24 12" aria-hidden="true">
            <line x1="0" y1="6" x2="24" y2="6" className={styles.outgoingLine} />
            <rect x="9" y="3" width="6" height="6" className={styles.outgoingMarker} />
          </svg>
          Outgoing / Dispatch
        </span>
      </div>

      <svg
        className={styles.plot}
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <polyline points={toPolylineAttr(incomingCoordinates)} className={styles.incomingLine} />
        <polyline points={toPolylineAttr(outgoingCoordinates)} className={styles.outgoingLine} />
        {incomingCoordinates.map((coordinate, index) => (
          <circle key={points[index].key} cx={coordinate.x} cy={coordinate.y} r="3" className={styles.incomingMarker} />
        ))}
        {outgoingCoordinates.map((coordinate, index) => (
          <rect
            key={points[index].key}
            x={coordinate.x - 3}
            y={coordinate.y - 3}
            width="6"
            height="6"
            className={styles.outgoingMarker}
          />
        ))}
      </svg>

      <div className={styles.axisLabels} aria-hidden="true">
        {selectAxisTicks(points).map(({ point, index }) => {
          const fraction = points.length === 1 ? 0.5 : index / (points.length - 1)
          const anchor = index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'
          return (
            <span
              key={point.key}
              className={styles.axisLabel}
              data-anchor={anchor}
              style={{ left: `${fraction * 100}%` }}
            >
              {point.label}
            </span>
          )
        })}
      </div>

      <details className={styles.dataTable}>
        <summary>View exact monthly counts</summary>
        <table>
          <caption className={styles.tableCaption}>
            Correspondence recorded per month, by direction
          </caption>
          <thead>
            <tr>
              <th scope="col">Month</th>
              <th scope="col">Incoming</th>
              <th scope="col">Outgoing</th>
            </tr>
          </thead>
          <tbody>
            {points.map((point) => (
              <tr key={point.key}>
                <th scope="row">{point.label}</th>
                <td>{point.incoming}</td>
                <td>{point.outgoing}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}
