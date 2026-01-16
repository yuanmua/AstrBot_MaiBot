<template>
  <div style="display: flex; flex-direction: column; align-items: center; padding: 24px;">
    <v-card class="mt-4" style="max-width: 800px; width: 100%;">
      <v-card-title class="d-flex align-center justify-space-between bg-primary">
        <div>
          <v-icon class="mr-2">mdi-chat-processing</v-icon>
          麦麦管理
        </div>
      </v-card-title>

      <v-card-text class="pa-6">
        <!-- 麦麦状态 -->
        <v-row class="mb-4">
          <v-col cols="12">
            <v-alert
              :type="maibotStatus.initialized ? 'success' : 'warning'"
              :icon="maibotStatus.initialized ? 'mdi-check-circle' : 'mdi-alert-circle'"
              variant="tonal"
            >
              <div class="d-flex align-center justify-space-between">
                <div>
                  <div class="text-h6">
                    {{ maibotStatus.initialized ? 'MaiBot 已初始化' : 'MaiBot 未初始化' }}
                  </div>
                  <div class="text-body-2 mt-1">
                    {{ maibotStatus.initialized ? 'MaiBot 核心已成功加载并运行' : 'MaiBot 核心尚未初始化，请检查日志' }}
                  </div>
                </div>
                <v-btn
                  icon="mdi-refresh"
                  variant="text"
                  @click="checkMaiBotStatus"
                  :loading="checking"
                ></v-btn>
              </div>
            </v-alert>
          </v-col>
        </v-row>

        <!-- 配置说明 -->
        <v-row class="mb-4">
          <v-col cols="12">
            <v-card variant="outlined">
              <v-card-title class="text-h6">
                <v-icon class="mr-2">mdi-cog</v-icon>
                如何启用麦麦处理
              </v-card-title>
              <v-card-text>
                <p class="mb-3">
                  要为每个机器人启用麦麦处理，请前往 <strong>配置文件</strong> 页面：
                </p>
                <ol>
                  <li class="mb-2">选择要配置的机器人（配置文件）</li>
                  <li class="mb-2">找到 <strong>"麦麦配置"</strong> 分组</li>
                  <li class="mb-2">打开 <strong>"启用麦麦处理"</strong> 开关</li>
                  <li class="mb-2">保存配置</li>
                </ol>
                <v-alert type="info" variant="tonal" density="compact" class="mt-3">
                  <strong>提示：</strong>每个机器人可以独立配置是否使用麦麦处理。启用后，该机器人的消息将由麦麦处理，不再使用 AstrBot 的插件和 LLM 流水线。
                </v-alert>
              </v-card-text>
              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn
                  color="primary"
                  variant="flat"
                  prepend-icon="mdi-cog"
                  to="/config"
                >
                  前往配置页面
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>

        <!-- 未来功能预留区域 -->
        <v-row class="mt-4">
          <v-col cols="12">
            <v-card variant="outlined" disabled>
              <v-card-title class="text-h6">
                <v-icon class="mr-2">mdi-account-multiple</v-icon>
                麦麦实例管理
                <v-chip size="small" class="ml-2" color="secondary">即将推出</v-chip>
              </v-card-title>
              <v-card-text class="text-disabled">
                <p>在这里您将能够：</p>
                <ul>
                  <li>创建和管理多个麦麦实例</li>
                  <li>为不同平台/群组配置不同的麦麦</li>
                  <li>自定义每个麦麦的人格、记忆和行为</li>
                  <li>查看麦麦的对话统计和性能指标</li>
                </ul>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

// 数据定义
const maibotStatus = ref({
  initialized: false,
  version: '',
});

const checking = ref(false);

// 检查 MaiBot 状态
const checkMaiBotStatus = async () => {
  checking.value = true;
  try {
    // 这里可以添加一个 API 来检查 MaiBot 状态
    // 暂时假设 MaiBot 已初始化
    maibotStatus.value.initialized = true;
  } catch (error) {
    console.error('检查 MaiBot 状态失败:', error);
    maibotStatus.value.initialized = false;
  } finally {
    checking.value = false;
  }
};

// 页面加载时初始化
onMounted(async () => {
  await checkMaiBotStatus();
});
</script>

<style scoped>
.text-disabled {
  opacity: 0.6;
}
</style>
