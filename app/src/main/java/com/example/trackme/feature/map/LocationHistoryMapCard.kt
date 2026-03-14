package com.example.trackme.feature.map

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.feature.common.SectionCard
import kotlin.math.max

@Composable
fun LocationHistoryMapCard(
    history: List<LocationSnapshot>,
    modifier: Modifier = Modifier
) {
    SectionCard(
        modifier = modifier,
        title = "Location history playback",
        eyebrow = "Bounded local view"
    ) {
        if (history.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(220.dp)
                    .background(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                        shape = RoundedCornerShape(20.dp)
                    ),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "No recent location history yet",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        } else {
            val projectedPoints = rememberProjectedPoints(history)
            val preciseColor = MaterialTheme.colorScheme.primary
            val moderateColor = MaterialTheme.colorScheme.tertiary
            val approximateColor = MaterialTheme.colorScheme.outline
            val gridColorStrong = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.45f)
            val gridColorSoft = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.35f)
            val routeColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.85f)

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(220.dp)
                    .background(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f),
                        shape = RoundedCornerShape(20.dp)
                    )
                    .padding(12.dp)
            ) {
                Canvas(modifier = Modifier.fillMaxWidth().height(196.dp)) {
                    val width = size.width
                    val height = size.height

                    repeat(4) { index ->
                        val y = height * index / 3f
                        drawLine(
                            color = gridColorStrong,
                            start = Offset(0f, y),
                            end = Offset(width, y),
                            strokeWidth = 1.dp.toPx()
                        )
                    }
                    repeat(4) { index ->
                        val x = width * index / 3f
                        drawLine(
                            color = gridColorSoft,
                            start = Offset(x, 0f),
                            end = Offset(x, height),
                            strokeWidth = 1.dp.toPx()
                        )
                    }

                    if (projectedPoints.size > 1) {
                        val route = Path().apply {
                            moveTo(projectedPoints.first().point.x * width, projectedPoints.first().point.y * height)
                            projectedPoints.drop(1).forEach { projected ->
                                lineTo(projected.point.x * width, projected.point.y * height)
                            }
                        }
                        drawPath(
                            path = route,
                            color = routeColor,
                            style = Stroke(width = 3.dp.toPx(), cap = StrokeCap.Round)
                        )
                    }

                    projectedPoints.forEach { projected ->
                        val pointOffset = Offset(projected.point.x * width, projected.point.y * height)
                        val color = when (projected.snapshot.precision) {
                            LocationPrecision.PRECISE -> preciseColor
                            LocationPrecision.MODERATE -> moderateColor
                            LocationPrecision.APPROXIMATE -> approximateColor
                        }
                        if (projected.snapshot.isApproximate) {
                            drawCircle(
                                color = color.copy(alpha = 0.22f),
                                radius = 11.dp.toPx(),
                                center = pointOffset,
                                style = Stroke(width = 2.dp.toPx())
                            )
                        }
                        drawCircle(
                            color = color.copy(alpha = 0.32f),
                            radius = 7.dp.toPx(),
                            center = pointOffset
                        )
                        drawCircle(
                            color = color,
                            radius = 3.5.dp.toPx(),
                            center = pointOffset
                        )
                    }
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                MapLegendItem(label = "Precise", color = preciseColor)
                MapLegendItem(label = "Moderate", color = moderateColor)
                MapLegendItem(label = "Approximate", color = approximateColor)
            }
        }
    }
}

@Composable
private fun MapLegendItem(
    label: String,
    color: Color
) {
    Row(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .background(color, RoundedCornerShape(999.dp))
                .padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.surface
            )
        }
    }
}

private data class ProjectedLocationPoint(
    val snapshot: LocationSnapshot,
    val point: Offset
)

private fun rememberProjectedPoints(history: List<LocationSnapshot>): List<ProjectedLocationPoint> {
    val minLat = history.minOf { it.latitude }
    val maxLat = history.maxOf { it.latitude }
    val minLng = history.minOf { it.longitude }
    val maxLng = history.maxOf { it.longitude }
    val latRange = max(maxLat - minLat, 0.001)
    val lngRange = max(maxLng - minLng, 0.001)

    return history.map { snapshot ->
        val normalizedX = ((snapshot.longitude - minLng) / lngRange).toFloat().coerceIn(0.08f, 0.92f)
        val normalizedY = (1f - ((snapshot.latitude - minLat) / latRange).toFloat()).coerceIn(0.08f, 0.92f)
        ProjectedLocationPoint(snapshot = snapshot, point = Offset(normalizedX, normalizedY))
    }
}
