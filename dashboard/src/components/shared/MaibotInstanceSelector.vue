<template>
  <div>
    <v-select
      :model-value="modelValue"
      @update:model-value="emitUpdate"
      :items="instanceItems"
      :loading="loading"
      :disabled="loading"
      density="compact"
      variant="outlined"
      class="config-field"
      hide-details
      :label="t('core.shared.maibotInstanceSelector.selectInstance')"
      :hint="t('core.shared.maibotInstanceSelector.hint')"
      persistent-hint
    >
      <template #no-data>
        <v-list-item>
          <v-list-item-title>{{ t('core.shared.maibotInstanceSelector.noInstances') }}</v-list-item-title>
        </v-list-item>
      </template>
    </v-select>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from '@/i18n/composables';

// API 响应接口
interface InstanceInfo {
  id: string;
  name: string;
  status: string;
  is_default: boolean;
}

interface ApiResponse<T> {
  status: string;
  message?: string;
  data?: T;
}

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  }
});

const emit = defineEmits(['update:modelValue']);

const { t } = useI18n();
const loading = ref(false);
const instances = ref<InstanceInfo[]>([]);

// 实例选项
const instanceItems = computed(() => {
  const items = instances.value.map(inst => ({
    title: inst.name + (inst.is_default ? ' (默认)' : ''),
    value: inst.id
  }));

  // 添加"使用默认实例"选项
  items.unshift({
    title: t('core.shared.maibotInstanceSelector.useDefault'),
    value: ''
  });

  return items;
});

// 获取运行中的实例列表
const fetchInstances = async () => {
  loading.value = true;
  try {
    const response = await fetch('/api/maibot/running');
    if (response.ok) {
      const data: ApiResponse<{ instances: InstanceInfo[] }> = await response.json();
      if (data.data?.instances) {
        instances.value = data.data.instances;
      }
    }
  } catch (error) {
    console.error('获取麦麦实例列表失败:', error);
  } finally {
    loading.value = false;
  }
};

function emitUpdate(val: string | number) {
  emit('update:modelValue', val);
}

onMounted(() => {
  fetchInstances();
});
</script>

<style scoped>
.config-field {
  margin-bottom: 0;
}
</style>
