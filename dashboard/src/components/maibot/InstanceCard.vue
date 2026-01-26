<template>
  <v-card class="instance-card" :class="{ 'is-default': instance.is_default }">
    <!-- 卡片头 -->
    <v-card-title class="d-flex justify-space-between align-center">
      <div class="flex-grow-1">
        <div class="d-flex align-center gap-2">
          <span class="text-h6">{{ instance.name }}</span>
          <v-chip
            v-if="instance.is_default"
            size="small"
            color="primary"
            variant="elevated"
          >
            {{ tm("instanceCard.isDefault") }}
          </v-chip>
        </div>
        <div class="text-caption text-grey">{{ instance.id }}</div>
      </div>
      <!-- 状态指示器 -->
      <div
        class="status-indicator"
        :class="`status-${instance.status}`"
        :title="statusText"
      >
        <v-icon :icon="statusIcon" :color="statusColor" size="large"></v-icon>
      </div>
    </v-card-title>

    <!-- 卡片内容 -->
    <v-card-text>
      <!-- 描述 -->
      <p v-if="instance.description" class="text-sm mb-3">
        {{ instance.description }}
      </p>

      <!-- 统计信息网格 -->
      <v-row class="mb-3" dense>
        <v-col cols="6">
          <div class="stat-item">
            <div class="stat-label">
              {{ tm("instanceCard.uptime") }}
            </div>
            <div class="stat-value">{{ formatUptime }}</div>
          </div>
        </v-col>
        <v-col cols="6">
          <div class="stat-item">
            <div class="stat-label">
              {{ tm("instanceCard.messageCount") }}
            </div>
            <div class="stat-value">{{ instance.message_count || 0 }}</div>
          </div>
        </v-col>
      </v-row>

      <!-- 时间和配置信息 -->
      <v-divider class="my-2"></v-divider>

      <div class="text-caption text-grey">
        <div class="d-flex justify-space-between py-1">
          <span>{{ tm("instanceCard.createdAt") }}:</span>
          <span>{{ formatDate(instance.created_at) }}</span>
        </div>
        <div class="d-flex justify-space-between py-1">
          <span>{{ tm("instanceCard.port") }}:</span>
          <span>{{ instance.port }}</span>
        </div>
        <div
          v-if="instance.enable_webui || instance.enable_socket"
          class="d-flex justify-space-between py-1"
        >
          <span>{{ tm("instanceCard.webui") }}:</span>
          <v-chip size="x-small" variant="outlined">
            {{ instance.enable_webui ? "✓" : "✗" }}
          </v-chip>
        </div>
      </div>

      <!-- 错误消息显示 -->
      <v-alert
        v-if="instance.status === 'error' && instance.error_message"
        type="error"
        class="mt-2"
        variant="tonal"
        density="compact"
      >
        {{ instance.error_message }}
      </v-alert>
    </v-card-text>

    <!-- 卡片操作 -->
    <v-card-actions class="pt-0">
      <v-spacer></v-spacer>

      <!-- 启动/停止按钮 -->
      <v-btn
        v-if="instance.status === 'stopped'"
        size="small"
        variant="elevated"
        color="success"
        @click="handleStart"
        :loading="isLoading"
      >
        {{ tm("operations.start") }}
      </v-btn>

      <v-btn
        v-else-if="instance.status === 'running'"
        size="small"
        variant="elevated"
        color="error"
        @click="handleStop"
        :loading="isLoading"
      >
        {{ tm("operations.stop") }}
      </v-btn>

      <v-btn v-else size="small" disabled>
        {{ statusText }}
      </v-btn>

      <!-- 更多操作菜单 -->
      <v-menu>
        <template #activator="{ props }">
          <v-btn
            size="small"
            icon="mdi-dots-vertical"
            variant="text"
            v-bind="props"
          ></v-btn>
        </template>

        <v-list>
          <v-list-item
            @click="handleRestart"
            :disabled="
              instance.status !== 'running' && instance.status !== 'stopped'
            "
          >
            <template #prepend>
              <v-icon icon="mdi-restart"></v-icon>
            </template>
            <v-list-item-title>{{
              tm("operations.restart")
            }}</v-list-item-title>
          </v-list-item>

          <v-list-item @click="handleEdit">
            <template #prepend>
              <v-icon icon="mdi-pencil"></v-icon>
            </template>
            <v-list-item-title>{{ tm("operations.edit") }}</v-list-item-title>
          </v-list-item>

          <v-divider></v-divider>

          <v-list-item @click="handleDelete" :disabled="instance.is_default">
            <template #prepend>
              <v-icon icon="mdi-delete" color="error"></v-icon>
            </template>
            <v-list-item-title class="text-error">
              {{ tm("operations.delete") }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { InstanceInfo } from "@/utils/features.maibotApi";
import { useInstances } from "@/composables/useInstances";
import { useModuleI18n } from "@/i18n/composables";
const { tm } = useModuleI18n("features/maibot");

interface Props {
  instance: InstanceInfo;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  start: [];
  stop: [];
  restart: [];
  edit: [];
  delete: [];
}>();

const { instanceLoading } = useInstances();

// 状态文本映射
const statusTextMap: Record<string, string> = {
  stopped: "已停止",
  starting: "启动中",
  running: "运行中",
  stopping: "停止中",
  error: "错误",
  restarting: "重启中",
};

// 状态图标映射
const statusIconMap: Record<string, string> = {
  stopped: "mdi-stop-circle-outline",
  starting: "mdi-loading mdi-spin",
  running: "mdi-play-circle",
  stopping: "mdi-loading mdi-spin",
  error: "mdi-alert-circle",
  restarting: "mdi-loading mdi-spin",
};

// 状态颜色映射
const statusColorMap: Record<string, string> = {
  stopped: "grey",
  starting: "warning",
  running: "success",
  stopping: "warning",
  error: "error",
  restarting: "info",
};

const statusText = computed(() => {
  const key = props.instance.status as keyof typeof statusTextMap;
  return statusTextMap[key] || "未知状态";
});

const statusIcon = computed(() => {
  const key = props.instance.status as keyof typeof statusIconMap;
  return statusIconMap[key] || "mdi-help-circle";
});

const statusColor = computed(() => {
  const key = props.instance.status as keyof typeof statusColorMap;
  return statusColorMap[key] || "grey";
});

const isLoading = computed(() => {
  return instanceLoading[props.instance.id] || false;
});

// 格式化运行时长
const formatUptime = computed(() => {
  if (!props.instance.uptime) {
    return props.instance.status === "running" ? "启动中..." : "-";
  }

  const seconds = Math.floor(props.instance.uptime);
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h`;
  } else if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else {
    return `${minutes}m`;
  }
});

// 格式化日期
const formatDate = (dateStr: string | undefined): string => {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    return date.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
};

// 事件处理
const handleStart = () => {
  emit("start");
};

const handleStop = () => {
  emit("stop");
};

const handleRestart = () => {
  emit("restart");
};

const handleEdit = () => {
  emit("edit");
};

const handleDelete = () => {
  emit("delete");
};
</script>

<style scoped lang="scss">
.instance-card {
  height: 100%;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  &.is-default {
    border-left: 4px solid #7c3aed;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    min-height: 40px;

    &.status-running {
      animation: pulse 2s infinite;
    }

    &.status-starting,
    &.status-stopping,
    &.status-restarting {
      animation: spin 1s linear infinite;
    }
  }

  .stat-item {
    padding: 8px;
    background: #f5f5f5;
    border-radius: 4px;
    text-align: center;

    .stat-label {
      font-size: 12px;
      color: #666;
      margin-bottom: 4px;
    }

    .stat-value {
      font-size: 16px;
      font-weight: bold;
      color: #333;
    }
  }
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
