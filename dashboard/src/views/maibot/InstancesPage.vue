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
        @click="goToCreate"
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
            @view-log="handleViewLogs(instance.id)"
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
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useToast } from "@/utils/toast";
import { useInstances } from "@/composables/useInstances";
import InstanceCard from "@/components/maibot/InstanceCard.vue";
import { useModuleI18n } from "@/i18n/composables";
const { tm } = useModuleI18n("features/maibot");

const router = useRouter();
const { success } = useToast();

const {
  instances,
  loading,
  error,
  refreshInstances,
  removeInstance,
  startInstanceAsync,
  stopInstanceAsync,
  restartInstanceAsync,
} = useInstances();

// UI 状态
const fab = ref(false);
const showDeleteDialog = ref(false);
const isDeleting = ref(false);
const selectedDeleteInstanceId = ref("");

// 删除表单
const deleteFormData = ref({
  deleteData: false,
});

// 跳转到创建页面
const goToCreate = () => {
  router.push("/maibot/create");
};

// 启动实例
const handleStartInstance = async (instanceId: string) => {
  const result = await startInstanceAsync(instanceId);

  if (result) {
    success("实例启动中...", { type: "success" });
  } else {
    success("启动实例失败", { type: "error" });
  }
};

// 停止实例
const handleStopInstance = async (instanceId: string) => {
  const result = await stopInstanceAsync(instanceId);

  if (result) {
    success("实例停止中...", { type: "success" });
  } else {
    success("停止实例失败", { type: "error" });
  }
};

// 重启实例
const handleRestartInstance = async (instanceId: string) => {
  const result = await restartInstanceAsync(instanceId);

  if (result) {
    success("实例重启中...", { type: "success" });
  } else {
    success("重启实例失败", { type: "error" });
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
      success("实例删除成功！", { type: "success" });
      showDeleteDialog.value = false;
    } else {
      success("删除实例失败", { type: "error" });
    }
  } finally {
    isDeleting.value = false;
  }
};

// 编辑实例（导航到详情页）
const handleEditInstance = (instanceId: string) => {
  router.push(`/maibot/instances/${instanceId}`);
};

// 查看日志（导航到日志页面）
const handleViewLogs = (instanceId: string) => {
  router.push(`/maibot/logs?instance=${instanceId}`);
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
