<template>
  <v-container fluid class="py-6">
    <!-- 页面头 -->
    <div class="d-flex justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h4 mb-2">{{ tm("title") }}</h1>
        <p class="text-grey">{{ tm("subtitle") }}</p>
      </div>
      <v-btn
        color="primary"
        size="large"
        prepend-icon="mdi-plus"
        @click="showCreateDialog = true"
      >
        {{ tm("addInstance") }}
      </v-btn>
    </div>

    <!-- 加载状态 -->
    <v-progress-linear
      v-if="loading"
      indeterminate
      class="mb-4"
    ></v-progress-linear>

    <!-- 错误提示 -->
    <v-alert
      v-if="error"
      type="error"
      class="mb-4"
      closable
      @click:close="error = null"
    >
      {{ error }}
    </v-alert>

    <!-- 实例网格 -->
    <div v-if="instances.length > 0">
      <v-row>
        <v-col
          v-for="instance in instances"
          :key="instance.id"
          cols="12"
          sm="6"
          md="4"
          lg="3"
        >
          <InstanceCard
            :instance="instance"
            @start="handleStartInstance(instance.id)"
            @stop="handleStopInstance(instance.id)"
            @restart="handleRestartInstance(instance.id)"
            @edit="handleEditInstance(instance.id)"
            @delete="handleDeleteInstance(instance.id)"
          />
        </v-col>
      </v-row>
    </div>

    <!-- 空状态 -->
    <v-empty-state
      v-else
      headline="暂无实例"
      :text="tm('emptyText')"
      icon="mdi-robot"
    ></v-empty-state>

    <!-- 创建实例对话框 -->
    <v-dialog v-model="showCreateDialog" max-width="500">
      <v-card>
        <v-card-title>{{ tm("dialog.create") }}</v-card-title>

        <v-card-text>
          <v-form ref="createForm" @submit.prevent="handleCreateInstance">
            <!-- 实例ID -->
            <v-text-field
              v-model="createFormData.instance_id"
              label="Instance ID"
              placeholder="e.g., my_bot"
              required
              @blur="validateInstanceId"
              :error-messages="createFormErrors.instance_id"
              class="mb-4"
            ></v-text-field>

            <!-- 实例名称 -->
            <v-text-field
              v-model="createFormData.name"
              :label="tm('instanceDetail.instanceName')"
              required
              class="mb-4"
            ></v-text-field>

            <!-- 描述 -->
            <v-textarea
              v-model="createFormData.description"
              :label="tm('instanceDetail.description')"
              rows="2"
              class="mb-4"
            ></v-textarea>

            <!-- 复制配置 -->
            <v-select
              v-model="createFormData.copy_from"
              :items="copyFromOptions"
              :label="tm('dialog.copyFrom')"
              clearable
              class="mb-4"
            ></v-select>

            <!-- 端口 -->
            <v-text-field
              v-model.number="createFormData.port"
              :label="tm('instanceDetail.port')"
              type="number"
              min="1000"
              max="65535"
              class="mb-4"
            ></v-text-field>

            <!-- 功能开关 -->
            <div class="d-flex gap-4 mb-4">
              <v-checkbox
                v-model="createFormData.enable_webui"
                :label="tm('instanceDetail.enableWebui')"
              ></v-checkbox>

              <v-checkbox
                v-model="createFormData.enable_socket"
                :label="tm('instanceDetail.enableSocket')"
              ></v-checkbox>
            </div>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showCreateDialog = false">
            {{ tm("dialog.cancel") }}
          </v-btn>
          <v-btn
            color="primary"
            @click="handleCreateInstance"
            :loading="isCreating"
          >
            {{ tm("dialog.confirm") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除确认对话框 -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ tm("dialog.delete") }}</v-card-title>

        <v-card-text>
          <p>{{ tm("dialog.deleteWarning") }}</p>

          <v-checkbox
            v-model="deleteFormData.deleteData"
            :label="tm('dialog.deleteDataOption')"
            class="mt-2"
          ></v-checkbox>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="showDeleteDialog = false">
            {{ tm("dialog.cancel") }}
          </v-btn>
          <v-btn
            color="error"
            @click="confirmDeleteInstance"
            :loading="isDeleting"
          >
            {{ tm("operations.delete") }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 操作按钮浮窗 -->
<!--    <v-speed-dial v-model="fab" direction="top" open-on-hover class="fixed-fab">-->
<!--      <template #activator="{ props }">-->
<!--        <v-btn-->
<!--          v-bind="props"-->
<!--          icon="mdi-menu"-->
<!--          size="large"-->
<!--          color="primary"-->
<!--        ></v-btn>-->
<!--      </template>-->

<!--      <v-btn icon="mdi-refresh" @click="refreshInstances" :loading="loading">-->
<!--        <v-tooltip text="刷新实例列表" location="left"></v-tooltip>-->
<!--      </v-btn>-->

<!--      <v-btn icon="mdi-routes" @click="goToRouting">-->
<!--        <v-tooltip text="路由管理" location="left"></v-tooltip>-->
<!--      </v-btn>-->

<!--      <v-btn icon="mdi-file-document" @click="goToLogs">-->
<!--        <v-tooltip text="查看日志" location="left"></v-tooltip>-->
<!--      </v-btn>-->
<!--    </v-speed-dial>-->
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "@/utils/toast";
import { useInstances } from "@/composables/useInstances";
import InstanceCard from "@/components/maibot/InstanceCard.vue";
import { useModuleI18n } from "@/i18n/composables";
const { tm } = useModuleI18n("features/maibot");

const router = useRouter();
const { toastSuccess: toastSuccess } = useToast();

const {
  instances,
  loading,
  error,
  refreshInstances,
  createNewInstance,
  removeInstance,
  startInstanceAsync,
  stopInstanceAsync,
  restartInstanceAsync,
} = useInstances();

// UI 状态
const fab = ref(false);
const showCreateDialog = ref(false);
const showDeleteDialog = ref(false);
const isCreating = ref(false);
const isDeleting = ref(false);
const selectedDeleteInstanceId = ref("");

// 创建表单
const createForm = ref();
const createFormData = ref({
  instance_id: "",
  name: "",
  description: "",
  port: 8001,
  copy_from: "",
  enable_webui: false,
  enable_socket: false,
});

const createFormErrors = ref<Record<string, string[]>>({
  instance_id: [],
});

// 删除表单
const deleteFormData = ref({
  deleteData: false,
});

// 复制源选项
const copyFromOptions = computed(() => {
  return instances.value.map((inst) => ({
    title: inst.name,
    value: inst.id,
  }));
});

// 验证实例ID
const validateInstanceId = () => {
  const id = createFormData.value.instance_id;
  createFormErrors.value.instance_id = [];

  if (!id) {
    createFormErrors.value.instance_id.push("实例ID不能为空");
    return false;
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(id)) {
    createFormErrors.value.instance_id.push(
      "实例ID只能包含字母、数字、下划线和连字符",
    );
    return false;
  }

  if (instances.value.some((i) => i.id === id)) {
    createFormErrors.value.instance_id.push("实例ID已存在");
    return false;
  }

  return true;
};

// 创建实例
const handleCreateInstance = async () => {
  if (!validateInstanceId()) {
    return;
  }

  isCreating.value = true;

  try {
    const result = await createNewInstance(createFormData.value);

    if (result) {
      toastSuccess("实例创建成功！", { type: "success" });

      // 重置表单
      createFormData.value = {
        instance_id: "",
        name: "",
        description: "",
        port: 8001,
        copy_from: "",
        enable_webui: false,
        enable_socket: false,
      };

      showCreateDialog.value = false;
    } else {
      toastSuccess("创建实例失败", { type: "error" });
    }
  } finally {
    isCreating.value = false;
  }
};

// 启动实例
const handleStartInstance = async (instanceId: string) => {
  const result = await startInstanceAsync(instanceId);

  if (result) {
    toastSuccess("实例启动中...", { type: "success" });
  } else {
    toastSuccess("启动实例失败", { type: "error" });
  }
};

// 停止实例
const handleStopInstance = async (instanceId: string) => {
  const result = await stopInstanceAsync(instanceId);

  if (result) {
    toastSuccess("实例停止中...", { type: "success" });
  } else {
    toastSuccess("停止实例失败", { type: "error" });
  }
};

// 重启实例
const handleRestartInstance = async (instanceId: string) => {
  const result = await restartInstanceAsync(instanceId);

  if (result) {
    toastSuccess("实例重启中...", { type: "success" });
  } else {
    toastSuccess("重启实例失败", { type: "error" });
  }
};

// 删除实例
const handleDeleteInstance = (instanceId: string) => {
  selectedDeleteInstanceId.value = instanceId;
  deleteFormData.value.deleteData = false;
  showDeleteDialog.value = true;
};

const confirmDeleteInstance = async () => {
  isDeleting.value = true;

  try {
    const result = await removeInstance(
      selectedDeleteInstanceId.value,
      deleteFormData.value.deleteData,
    );

    if (result) {
      toastSuccess("实例删除成功！", { type: "success" });
      showDeleteDialog.value = false;
    } else {
      toastSuccess("删除实例失败", { type: "error" });
    }
  } finally {
    isDeleting.value = false;
  }
};

// 编辑实例（导航到详情页）
const handleEditInstance = (instanceId: string) => {
  router.push(`/maibot/instances/${instanceId}`);
};

// 导航
const goToRouting = () => {
  router.push("/maibot/routing");
};

const goToLogs = () => {
  router.push("/maibot/logs");
};

// 初始化
onMounted(() => {
  refreshInstances();
});
</script>

<style scoped lang="scss">
.fixed-fab {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
}
</style>
