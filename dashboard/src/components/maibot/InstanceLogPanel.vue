<template>
  <v-card>
    <!-- 标题和工具栏 -->
    <v-card-title class="d-flex justify-space-between align-center">
      <span>{{ tm("logPanel.title") }} - {{ instanceId }}</span>
      <div class="d-flex gap-2">
        <!-- 日志级别过滤 -->
        <v-select
          v-model="selectedLogLevel"
          :items="logLevels"
          density="compact"
          style="width: 120px"
          class="text-caption"
        ></v-select>

        <!-- 搜索框 -->
        <v-text-field
          v-model="searchText"
          :placeholder="$t('features.maibot.logPanel.filter')"
          density="compact"
          prepend-inner-icon="mdi-magnify"
          clearable
          style="width: 200px"
        ></v-text-field>

        <!-- 操作按钮 -->
        <v-btn
          icon="mdi-refresh"
          size="small"
          @click="refreshLogs"
          :loading="loading"
        ></v-btn>

        <v-menu>
          <template #activator="{ props }">
            <v-btn icon="mdi-dots-vertical" size="small" v-bind="props"></v-btn>
          </template>

          <v-list>
            <v-list-item @click="toggleRealtime">
              <template #prepend>
                <v-icon
                  :icon="isRealtimeEnabled ? 'mdi-play' : 'mdi-pause'"
                ></v-icon>
              </template>
              <v-list-item-title>
                {{
                  isRealtimeEnabled
                    ? tm("logPanel.realtime")
                    : "暂停实时"
                }}
              </v-list-item-title>
            </v-list-item>

            <v-list-item @click="downloadLogs">
              <template #prepend>
                <v-icon icon="mdi-download"></v-icon>
              </template>
              <v-list-item-title>{{
                tm("logPanel.download")
              }}</v-list-item-title>
            </v-list-item>

            <v-divider></v-divider>

            <v-list-item @click="showClearConfirm = true" class="text-error">
              <template #prepend>
                <v-icon icon="mdi-trash-can" color="error"></v-icon>
              </template>
              <v-list-item-title>{{
                tm("logPanel.clear")
              }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>
    </v-card-title>

    <!-- 日志显示区域 -->
    <v-divider></v-divider>

    <v-card-text class="log-container pa-0">
      <div v-if="filteredLogs.length === 0" class="text-center text-grey pa-4">
        {{ tm("logPanel.noLogs") }}
      </div>

      <div v-else class="log-list">
        <div
          v-for="(log, index) in filteredLogs"
          :key="index"
          class="log-line"
          :class="getLogClass(log)"
        >
          <span class="log-time">{{ extractTimestamp(log) }}</span>
          <span class="log-level">{{ extractLogLevel(log) }}</span>
          <span class="log-message">{{ log }}</span>
        </div>
      </div>
    </v-card-text>

    <!-- 清空确认对话框 -->
    <v-dialog v-model="showClearConfirm" max-width="400">
      <v-card>
        <v-card-title>{{ tm("logPanel.clear") }}</v-card-title>
        <v-card-text>
          {{ tm("logPanel.clearConfirm") }}
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showClearConfirm = false">
            {{ tm("dialog.cancel") }}
          </v-btn>
          <v-btn color="error" @click="handleClearLogs">
            {{ tm("logPanel.clear") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from "vue";
import { useInstances } from "@/composables/useInstances";
import { useToast } from "@/utils/toast";
const { tm } = useModuleI18n("features/maibot");

interface Props {
  instanceId: string;
}

const props = defineProps<Props>();

const {
  instanceLogs,
  instanceErrors,
  fetchInstanceLogs,
  clearInstanceLogsAsync,
  downloadInstanceLogsAsync,
} = useInstances();

const { toastSuccess: toastSuccess } = useToast();

// 状态
const loading = ref(false);
const searchText = ref("");
const selectedLogLevel = ref("all");
const showClearConfirm = ref(false);
const isRealtimeEnabled = ref(true);

// 日志级别选项
const logLevels = [
  { title: "All", value: "all" },
  { title: "DEBUG", value: "DEBUG" },
  { title: "INFO", value: "INFO" },
  { title: "WARNING", value: "WARNING" },
  { title: "ERROR", value: "ERROR" },
  { title: "CRITICAL", value: "CRITICAL" },
];

// 获取当前日志
const currentLogs = computed(() => {
  return instanceLogs[props.instanceId] || [];
});

// 过滤日志
const filteredLogs = computed(() => {
  return currentLogs.value.filter((log) => {
    // 日志级别过滤
    if (selectedLogLevel.value !== "all") {
      if (!log.includes(selectedLogLevel.value)) {
        return false;
      }
    }

    // 搜索文本过滤
    if (searchText.value) {
      return log.toLowerCase().includes(searchText.value.toLowerCase());
    }

    return true;
  });
});

// 提取日志时间戳
const extractTimestamp = (log: string): string => {
  const match = log.match(/\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]/);
  return match ? match[1] : "";
};

// 提取日志级别
const extractLogLevel = (log: string): string => {
  const levelMatch = log.match(/\[(DEBUG|INFO|WARNING|ERROR|CRITICAL)\]/);
  return levelMatch ? levelMatch[1] : "INFO";
};

// 获取日志样式类
const getLogClass = (log: string): string => {
  if (log.includes("ERROR") || log.includes("CRITICAL")) {
    return "log-error";
  } else if (log.includes("WARNING")) {
    return "log-warning";
  } else if (log.includes("DEBUG")) {
    return "log-debug";
  }
  return "log-info";
};

// 刷新日志
const refreshLogs = async () => {
  loading.value = true;
  try {
    await fetchInstanceLogs(props.instanceId, 200);
  } catch (err) {
    toastSuccess(instanceErrors[props.instanceId] || "加载日志失败", {
      type: "error",
    });
  } finally {
    loading.value = false;
  }
};

// 清空日志
const handleClearLogs = async () => {
  loading.value = true;
  showClearConfirm.value = false;

  try {
    await clearInstanceLogsAsync(props.instanceId);
    toastSuccess("日志已清空", { type: "toastSuccess" });
  } catch (err) {
    toastSuccess(instanceErrors[props.instanceId] || "清空日志失败", {
      type: "error",
    });
  } finally {
    loading.value = false;
  }
};

// 下载日志
const downloadLogs = async () => {
  loading.value = true;

  try {
    await downloadInstanceLogsAsync(props.instanceId);
    toastSuccess("日志已下载", { type: "toastSuccess" });
  } catch (err) {
    toastSuccess(instanceErrors[props.instanceId] || "下载日志失败", {
      type: "error",
    });
  } finally {
    loading.value = false;
  }
};

// 切换实时日志
const toggleRealtime = () => {
  isRealtimeEnabled.value = !isRealtimeEnabled.value;
};

// 自动刷新日志
let refreshInterval: NodeJS.Timeout | null = null;

const startAutoRefresh = () => {
  if (refreshInterval) clearInterval(refreshInterval);

  refreshInterval = setInterval(() => {
    if (isRealtimeEnabled.value) {
      fetchInstanceLogs(props.instanceId, 200);
    }
  }, 5000); // 每5秒刷新一次
};

const stopAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
};

// 监听 instanceId 变化
watch(
  () => props.instanceId,
  () => {
    refreshLogs();
  },
);

// 监听实时状态变化
watch(isRealtimeEnabled, (enabled) => {
  if (enabled) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
});

// 生命周期
onMounted(() => {
  refreshLogs();
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped lang="scss">
.log-container {
  height: 400px;
  background: #f5f5f5;
  overflow: hidden;
  display: flex;
  flex-direction: column;

  .log-list {
    flex: 1;
    overflow-y: auto;
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: "Monaco", "Menlo", "Ubuntu Mono", monospace;
    font-size: 12px;
    padding: 8px;
  }

  .log-line {
    padding: 2px 0;
    line-height: 1.5;
    display: flex;
    gap: 8px;
    border-bottom: 1px solid #333;

    &:hover {
      background: #252525;
    }

    .log-time {
      color: #858585;
      min-width: 180px;
      flex-shrink: 0;
    }

    .log-level {
      min-width: 80px;
      flex-shrink: 0;
      font-weight: bold;
      padding: 0 4px;
      border-radius: 2px;
    }

    .log-message {
      flex: 1;
      word-break: break-all;
    }

    &.log-error {
      color: #f48771;

      .log-level {
        color: #f48771;
        background: rgba(244, 135, 113, 0.1);
      }
    }

    &.log-warning {
      color: #ce9178;

      .log-level {
        color: #ce9178;
        background: rgba(206, 145, 120, 0.1);
      }
    }

    &.log-debug {
      color: #9cdcfe;

      .log-level {
        color: #9cdcfe;
        background: rgba(156, 220, 254, 0.1);
      }
    }

    &.log-info {
      color: #b4cea8;

      .log-level {
        color: #b4cea8;
        background: rgba(180, 206, 168, 0.1);
      }
    }
  }
}
</style>
