var timer = null
var countdownTimer = null
var deviceId = 'test_device_01'
var BASE_URL = 'http://192.168.1.21:8000'

function getQueue() {
  return wx.getStorageSync('heartbeat_queue') || []
}

function saveQueue(queue) {
  wx.setStorageSync('heartbeat_queue', queue)
}

function flushQueue(ctx) {
  var queue = getQueue()
  if (queue.length === 0) return

  console.log('flushQueue: 发送 %d 条心跳', queue.length)

  wx.request({
    url: BASE_URL + '/heartbeat',
    method: 'POST',
    header: { 'Content-Type': 'application/json' },
    data: queue,
    success: function (r) {
      console.log('flushQueue 成功: %d 条已送达', queue.length)
      saveQueue([])
      console.log('flushQueue: 队列已清空')
      fetchStatus(ctx)
    },
    fail: function (err) {
      console.log('flushQueue 失败: 网络异常，心跳保留在本地队列 (%d 条)', queue.length)
    }
  })
}

function tick(ctx) {
  wx.getLocation({
    type: 'wgs84',
    success: function (res) {
      var now = Math.floor(Date.now() / 1000)
      var item = {
        device_id: deviceId,
        latitude: res.latitude,
        longitude: res.longitude,
        client_ts: now,
        type: 'physical'
      }

      var queue = getQueue()
      queue.push(item)
      saveQueue(queue)
      console.log('tick: 位置获取成功，队列 %d 条', queue.length)

      var timeStr = formatTime(now)
      ctx.setData({ lastHeartbeat: timeStr, countdown: 60 })

      flushQueue(ctx)
    },
    fail: function (err) {
      console.log('tick: 位置获取失败，跳过本周期', err)
    }
  })
}

function fetchStatus(ctx) {
  wx.request({
    url: BASE_URL + '/status',
    method: 'GET',
    success: function (r) {
      if (r.data && r.data.state) {
        ctx.setData({ state: r.data.state })
      }
    },
    fail: function () {}
  })
}

function formatTime(ts) {
  var d = new Date(ts * 1000)
  var h = ('0' + d.getHours()).slice(-2)
  var m = ('0' + d.getMinutes()).slice(-2)
  var s = ('0' + d.getSeconds()).slice(-2)
  return h + ':' + m + ':' + s
}

Page({
  data: {
    protecting: false,
    state: '未知',
    lastHeartbeat: '--:--:--',
    countdown: 60,
    sosPressing: false
  },

  toggleProtection: function () {
    if (this.data.protecting) {
      this.stopProtection()
    } else {
      this.startProtection()
    }
  },

  startProtection: function () {
    if (timer) return
    var ctx = this

    console.log('startProtection: 开启守护')
    saveQueue([])
    ctx.setData({ protecting: true, countdown: 60 })
    tick(ctx)

    timer = setInterval(function () {
      tick(ctx)
    }, 60000)

    countdownTimer = setInterval(function () {
      var c = ctx.data.countdown
      if (c > 0) {
        ctx.setData({ countdown: c - 1 })
      }
    }, 1000)
  },

  stopProtection: function () {
    if (!timer) return

    clearInterval(timer)
    timer = null
    clearInterval(countdownTimer)
    countdownTimer = null
    console.log('stopProtection: 守护已停止')
    this.setData({ protecting: false, countdown: 60 })
  },

  manualPing: function () {
    var ctx = this
    console.log('manualPing: 手动确认心跳')
    tick(ctx)
  },

  onSosTouch: function () {
    var ctx = this
    ctx.sosStartTime = Date.now()
    ctx.setData({ sosPressing: true })
    ctx._sosTimer = setTimeout(function () {
      ctx.setData({ sosPressing: false })
      ctx._fireSos()
    }, 3000)
  },

  onSosRelease: function () {
    var ctx = this
    if (ctx._sosTimer) {
      clearTimeout(ctx._sosTimer)
      ctx._sosTimer = null
    }
    ctx.setData({ sosPressing: false })
    var elapsed = Date.now() - (ctx.sosStartTime || 0)
    if (elapsed < 2800) {
      wx.showToast({ title: '请长按 3 秒触发', icon: 'none' })
    }
  },

  _fireSos: function () {
    var ctx = this
    var now = Date.now()
    if (ctx._sosCooldown && now - ctx._sosCooldown < 15000) {
      console.log('SOS: 冷却中，忽略')
      return
    }
    ctx._sosCooldown = now
    console.log('SOS: 触发')

    wx.getLocation({
      type: 'wgs84',
      success: function (res) {
        var ts = Math.floor(Date.now() / 1000)
        wx.request({
          url: BASE_URL + '/sos/',
          method: 'POST',
          header: { 'Content-Type': 'application/json' },
          data: {
            latitude: res.latitude,
            longitude: res.longitude,
            client_ts: ts
          },
          success: function (r) {
            console.log('SOS 发送成功:', r.data)
            wx.showToast({ title: 'SOS 已发送', icon: 'none', duration: 3000 })
            fetchStatus(ctx)
          },
          fail: function (err) {
            console.log('SOS 发送失败:', err)
            wx.showToast({ title: 'SOS 发送失败', icon: 'error' })
          }
        })
      },
      fail: function (err) {
        console.log('SOS 定位失败:', err)
        wx.showToast({ title: '定位失败', icon: 'error' })
      }
    })
  }
})
