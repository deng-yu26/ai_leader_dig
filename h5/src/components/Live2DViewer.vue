<template>
  <!-- Live2D数字人渲染组件 -->
  <div class="live2d-viewer" ref="viewerRef">
    <!-- 加载状态 -->
    <div class="loading-placeholder" v-if="!loaded">
      <div class="model-icon">🪷</div>
      <p class="loading-text">数字人加载中...</p>
      <van-loading type="spinner" size="20" color="#c8a45c" />
    </div>

    <!-- Canvas渲染区域 -->
    <canvas ref="canvasRef" class="live2d-canvas" v-show="loaded"></canvas>

    <!-- 待机动画提示 -->
    <div class="idle-tip" v-if="loaded && !isSpeaking && emotion === '平静'">
      点击数字人互动
    </div>
  </div>
</template>

<script setup>
/**
 * Live2D数字人渲染组件
 * 基于Live2D Cubism Web SDK，集成表情映射与口型驱动
 *
 * 注意：实际使用时需要将Live2D SDK文件放置在 public/live2d_models/ 目录下
 * 当前为占位实现，展示了完整的接口架构
 *
 * Live2D模型文件结构要求：
 * public/live2d_models/
 *   ├── lingyun/         # 灵韵（默认导游）
 *   │   ├── model.json
 *   │   ├── *.model3.json
 *   │   └── *.moc3
 *   ├── huixin/          # 慧心（禅意导游）
 *   └── mingyuan/        # 明远（文化导游）
 */
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  emotion: { type: String, default: '平静' },     // 当前情绪：平静/微笑/热情
  isSpeaking: { type: Boolean, default: false },   // 是否正在说话
  dhId: { type: Number, default: 1 }               // 数字人ID
})

const viewerRef = ref(null)
const canvasRef = ref(null)
const loaded = ref(false)

// 模拟Live2D初始化（实际项目中替换为Cubism SDK初始化代码）
let animationTimer = null

onMounted(() => {
  // 模拟模型加载（实际项目中调用Live2D Cubism SDK初始化）
  setTimeout(() => {
    loaded.value = true
    startIdleAnimation()
  }, 1500)

  // 监听窗口变化
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  if (animationTimer) {
    clearInterval(animationTimer)
  }
  window.removeEventListener('resize', onResize)
})

// 监听情绪变化 - 切换面部表情
watch(() => props.emotion, (newEmotion) => {
  if (loaded.value) {
    setExpression(newEmotion)
  }
})

// 监听说话状态 - 控制口型动画
watch(() => props.isSpeaking, (speaking) => {
  if (speaking) {
    startLipSync()
  } else {
    stopLipSync()
    startIdleAnimation()
  }
})

// 监听数字人切换 - 重新加载模型
watch(() => props.dhId, () => {
  loaded.value = false
  setTimeout(() => {
    loaded.value = true
    startIdleAnimation()
  }, 1000)
})

// ============ Live2D控制接口（占位实现） ============

/**
 * 加载Live2D模型
 * @param {string} modelPath 模型文件路径
 */
function loadModel(modelPath) {
  // 实际实现：Live2D Cubism SDK 模型加载
  // const model = await Live2DModel.load(modelPath)
  // this.model = model
  // this.app.stage.addChild(model)
  console.log(`[Live2D] 加载模型: ${modelPath}`)
}

/**
 * 设置面部表情
 * @param {string} emotion 情绪标签
 *
 * 表情映射规则：
 * - 平静: 默认中性表情
 * - 微笑: 嘴角上扬，眼部微弯
 * - 热情: 大幅微笑，眼睛发亮，眉毛上扬
 */
function setExpression(emotion) {
  const expressionParams = {
    '平静': { mouthOpen: 0, eyeOpen: 1, browAngle: 0 },
    '微笑': { mouthOpen: 0.2, eyeOpen: 0.9, browAngle: 0.1 },
    '热情': { mouthOpen: 0.4, eyeOpen: 1, browAngle: 0.3 }
  }

  const params = expressionParams[emotion] || expressionParams['平静']

  // 实际实现：调用Live2D模型参数设置
  // if (this.model) {
  //   this.model.internalModel.coreModel.setParameterValueById('ParamMouthOpenY', params.mouthOpen)
  //   this.model.internalModel.coreModel.setParameterValueById('ParamEyeLOpen', params.eyeOpen)
  //   this.model.internalModel.coreModel.setParameterValueById('ParamEyeROpen', params.eyeOpen)
  //   this.model.internalModel.coreModel.setParameterValueById('ParamBrowLY', params.browAngle)
  //   this.model.internalModel.coreModel.setParameterValueById('ParamBrowRY', params.browAngle)
  // }
  console.log(`[Live2D] 设置表情: ${emotion}`, params)
}

/**
 * 口型同步驱动（基于音频波形）
 * 根据音频能量值实时调整嘴部张开度
 */
function startLipSync() {
  // 实际实现：使用AudioContext分析音频波形驱动口型
  // const audioCtx = new AudioContext()
  // const analyser = audioCtx.createAnalyser()
  // analyser.fftSize = 256
  // ...
  console.log('[Live2D] 启动口型同步')
}

function stopLipSync() {
  console.log('[Live2D] 停止口型同步')
}

/**
 * 循环待机动（呼吸、轻微晃动）
 */
function startIdleAnimation() {
  if (animationTimer) {
    clearInterval(animationTimer)
  }

  // 模拟呼吸动画
  let breathPhase = 0
  animationTimer = setInterval(() => {
    breathPhase += 0.05
    const breath = Math.sin(breathPhase) * 0.03

    // 实际实现：设置模型呼吸参数
    // if (this.model) {
    //   this.model.internalModel.coreModel.addParameterValueById('ParamBodyAngleX', breath)
    //   this.model.internalModel.coreModel.addParameterValueById('ParamBodyAngleY', Math.sin(breathPhase * 0.5) * 0.02)
    // }
  }, 50)
}

function onResize() {
  // 实际实现：更新canvas尺寸和模型投影矩阵
  console.log('[Live2D] 窗口大小变化')
}
</script>

<style scoped>
.live2d-viewer {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
}

.live2d-canvas {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.loading-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.model-icon {
  font-size: 80px;
  animation: float 2s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.loading-text {
  font-size: 14px;
  color: #6b7c6b;
}

.idle-tip {
  position: absolute;
  bottom: 20px;
  font-size: 12px;
  color: #9aab9a;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}
</style>