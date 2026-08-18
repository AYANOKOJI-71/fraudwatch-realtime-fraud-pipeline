import { describe, expect, it } from 'vitest'

import { actionLabel, compactLatency, ruleLabel } from './format'

describe('analyst display formatting', () => {
  it('formats decision labels and rule names', () => {
    expect(actionLabel('review')).toBe('Review')
    expect(ruleLabel('cross_border')).toBe('cross border')
  })

  it('keeps sub-millisecond processor latency visible', () => {
    expect(compactLatency(0.125)).toBe('0.125 ms')
  })
})
