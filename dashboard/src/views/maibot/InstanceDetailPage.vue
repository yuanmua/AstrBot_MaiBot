<template>
  <v-container fluid class="py-6">
    <!-- 返回按钮 -->
    <v-btn prepend-icon="mdi-arrow-left" @click="$router.back()" class="mb-4">
      返回列表
    </v-btn>

    <v-progress-linear
      v-if="loading"
      indeterminate
      class="mb-4"
    ></v-progress-linear>

    <v-alert
      v-if="error"
      type="error"
      class="mb-4"
      closable
      @click:close="error = null"
    >
      {{ error }}
    </v-alert>

    <v-row v-if="currentInstance">
      <!-- 左侧：实例信息卡片 -->
      <v-col cols="12" md="4">
        <!-- 实例状态卡片 -->
        <v-card class="mb-4">
          <v-card-title>{{ currentInstance.name }}</v-card-title>

          <v-card-text>
            <div class="mb-4">
              <div class="text-caption text-grey">状态</div>
              <div class="d-flex align-center gap-2 mt-1">
                <v-chip
                  :color="getStatusColor(currentInstance.status)"
                  size="small"
                >
                  {{ getStatusText(currentInstance.status) }}
                </v-chip>
              </div>
            </div>

            <v-divider class="my-3"></v-divider>

            <div class="mb-3">
              <div class="text-caption text-grey">基本信息</div>
              <div class="text-sm mt-2">
                <div class="d-flex justify-space-between py-1">
                  <span>ID:</span>
                  <span class="font-weight-bold">{{ currentInstance.id }}</span>
                </div>
                <div class="d-flex justify-space-between py-1">
                  <span>端口:</span>
                  <span>{{ currentInstance.port }}</span>
                </div>
                <div class="d-flex justify-space-between py-1">
                  <span>创建时间:</span>
                  <span>{{ formatDate(currentInstance.created_at) }}</span>
                </div>
              </div>
            </div>

            <v-divider class="my-3"></v-divider>

            <!-- 操作按钮 -->
            <div class="d-flex gap-2 flex-wrap">
              <v-btn
                v-if="currentInstance.status === 'stopped'"
                size="small"
                color="success"
                @click="handleStart"
                :loading="operationLoading"
              >
                启动
              </v-btn>

              <v-btn
                v-else-if="currentInstance.status === 'running'"
                size="small"
                color="error"
                @click="handleStop"
                :loading="operationLoading"
              >
                停止
              </v-btn>

              <v-btn
                size="small"
                @click="handleRestart"
                :disabled="
                  currentInstance.status !== 'running' &&
                  currentInstance.status !== 'stopped'
                "
                :loading="operationLoading"
              >
                重启
              </v-btn>

              <v-btn size="small" variant="outlined" @click="handleRefresh">
                刷新
              </v-btn>
            </div>
          </v-card-text>
        </v-card>

        <!-- 日志面板（简化版） -->
        <v-card>
          <v-card-title>最近日志</v-card-title>
          <v-card-text>
            <div class="log-preview" v-if="latestLogs.length > 0">
              <div
                v-for="(log, idx) in latestLogs.slice(0, 5)"
                :key="idx"
                class="text-caption text-grey"
              >
                {{ log }}
              </div>
            </div>
            <div v-else class="text-caption text-grey text-center py-3">
              暂无日志
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧：配置编辑标签页 -->
      <v-col cols="12" md="8">
        <v-card>
          <v-tabs v-model="activeTab">
            <v-tab value="basic">{{
              tm("instanceDetail.basicInfo")
            }}</v-tab>
            <v-tab value="personality">{{
              tm("instanceDetail.personality")
            }}</v-tab>
            <v-tab value="chat">{{
              tm("instanceDetail.chatConfig")
            }}</v-tab>
          </v-tabs>

          <v-divider></v-divider>

          <v-window v-model="activeTab" class="pa-4">
            <!-- 基本信息标签页 -->
            <v-window-item value="basic">
              <v-form ref="basicForm">
                <v-text-field
                  v-model="formData.name"
                  :label="tm('instanceDetail.instanceName')"
                  class="mb-4"
                ></v-text-field>

                <v-textarea
                  v-model="formData.description"
                  :label="tm('instanceDetail.description')"
                  rows="3"
                  class="mb-4"
                ></v-textarea>

                <v-text-field
                  v-model.number="formData.port"
                  :label="tm('instanceDetail.port')"
                  type="number"
                  min="1000"
                  max="65535"
                  class="mb-4"
                ></v-text-field>

                <v-switch
                  v-model="formData.enable_webui"
                  :label="tm('instanceDetail.enableWebui')"
                  class="mb-2"
                ></v-switch>

                <v-switch
                  v-model="formData.enable_socket"
                  :label="tm('instanceDetail.enableSocket')"
                ></v-switch>
              </v-form>
            </v-window-item>

            <!-- 人格配置标签页 -->
            <v-window-item value="personality">
              <v-form ref="personalityForm">
                <v-textarea
                  v-model="formData.personality"
                  label="人格描述"
                  rows="6"
                  class="mb-4"
                ></v-textarea>

                <v-textarea
                  v-model="formData.reply_style"
                  label="回复风格"
                  rows="4"
                ></v-textarea>
              </v-form>
            </v-window-item>

            <!-- 聊天配置标签页 -->
            <v-window-item value="chat">
              <v-form ref="chatForm">
                <v-slider
                  v-model="formData.talk_value"
                  label="话题活跃度"
                  min="0"
                  max="1"
                  step="0.1"
                  class="mb-4"
                ></v-slider>

                <v-text-field
                  v-model.number="formData.max_context_size"
                  label="最大上下文大小"
                  type="number"
                  min="1"
                  max="100"
                ></v-text-field>
              </v-form>
            </v-window-item>
          </v-window>

          <!-- 保存按钮 -->
          <v-divider></v-divider>

          <v-card-actions class="pa-4">
            <v-spacer></v-spacer>
            <v-btn @click="$router.back()">
              {{ tm("instanceDetail.cancel") }}
            </v-btn>
            <v-btn color="primary" @click="handleSave" :loading="isSaving">
              {{ tm("instanceDetail.save") }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useToast } from "@/utils/toast";
import { useModuleI18n } from "@/i18n/composables";
const { tm } = useModuleI18n("features/maibot");

const route = useRoute();
const { success: success } = useToast();

const {
  instances,
  instanceLogs,
  loading,
  instanceLoading,
  instanceErrors,
  refreshInstances,
  fetchInstance,
  fetchInstanceLogs,
  startInstanceAsync,
  stopInstanceAsync,
  restartInstanceAsync,
  saveInstanceConfigAsync,
} = useInstances();

const instanceId = route.params.id as string;

// UI 状态
const activeTab = ref("basic");
const isSaving = ref(false);
const operationLoading = ref(false);
const error = ref<string | null>(null);

// 当前实例
const currentInstance = computed(() => {
  return instances.value.find((i) => i.id === instanceId);
});

// 最近日志
const latestLogs = computed(() => {
  return instanceLogs[instanceId] || [];
});

// 表单数据
const formData = reactive({
  name: "",
  description: "",
  port: 8001,
  enable_webui: false,
  enable_socket: false,
  personality: "",
  reply_style: "",
  talk_value: 0.5,
  max_context_size: 20,
});

// 初始化表单数据
const initializeFormData = () => {
  if (currentInstance.value) {
    formData.name = currentInstance.value.name;
    formData.description = currentInstance.value.description;
    formData.port = currentInstance.value.port;
    formData.enable_webui = currentInstance.value.enable_webui;
    formData.enable_socket = currentInstance.value.enable_socket;
  }
};

// 状态工具函数
const getStatusText = (status: string): string => {
  const map: Record<string, string> = {
    stopped: "已停止",
    starting: "启动中",
    running: "运行中",
    stopping: "停止中",
    error: "错误",
    restarting: "重启中",
  };
  return map[status] || "未知";
};

const getStatusColor = (status: string): string => {
  const map: Record<string, string> = {
    stopped: "grey",
    starting: "warning",
    running: "success",
    stopping: "warning",
    error: "error",
    restarting: "info",
  };
  return map[status] || "grey";
};

const formatDate = (dateStr: string | undefined): string => {
  if (!dateStr) return "-";
  try {
    const date = new Date(dateStr);
    return date.toLocaleString("zh-CN");
  } catch {
    return dateStr;
  }
};

// 操作处理函数
const handleStart = async () => {
  operationLoading.value = true;
  try {
    await startInstanceAsync(instanceId);
    success("实例启动中...", { type: "success" });
    handleRefresh();
  } finally {
    operationLoading.value = false;
  }
};

const handleStop = async () => {
  operationLoading.value = true;
  try {
    await stopInstanceAsync(instanceId);
    success("实例停止中...", { type: "success" });
    handleRefresh();
  } finally {
    operationLoading.value = false;
  }
};

const handleRestart = async () => {
  operationLoading.value = true;
  try {
    await restartInstanceAsync(instanceId);
    success("实例重启中...", { type: "success" });
    handleRefresh();
  } finally {
    operationLoading.value = false;
  }
};

const handleRefresh = async () => {
  await refreshInstances();
  await fetchInstanceLogs(instanceId, 100);
};

const handleSave = async () => {
  isSaving.value = true;
  try {
    const result = await saveInstanceConfigAsync(instanceId, formData);

    if (result) {
      success("配置已保存", { type: "success" });
    } else {
      success("保存失败", { type: "error" });
    }
  } finally {
    isSaving.value = false;
  }
};

// 初始化
onMounted(async () => {
  await refreshInstances();
  await fetchInstanceLogs(instanceId, 100);
  initializeFormData();
});
</script>

<style scoped lang="scss">
.log-preview {
  font-family: monospace;
  font-size: 11px;
  max-height: 200px;
  overflow-y: auto;
  background: #f5f5f5;
  padding: 8px;
  border-radius: 4px;
  line-height: 1.4;
}
</style>
