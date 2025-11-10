'use client'

import { useState } from 'react'
import { Sidebar } from '@/components/Sidebar'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { Container } from '@/components/ui/Container'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'

type ChineseDivinationType = 'bazi' | 'liuyao' | null

export default function ChineseDivinationPage() {
  const [selectedType, setSelectedType] = useState<ChineseDivinationType>(null)

  return (
    <ProtectedRoute>
      <Sidebar>
        <div 
          className="min-h-screen py-12"
          style={{ 
            backgroundColor: '#d4b896',
            backgroundImage: 'linear-gradient(135deg, #d4b896 0%, #c4a57b 50%, #d4b896 100%)'
          }}
        >
          <Container size="lg" className="w-full">
            <div className="flex flex-col items-center space-y-10">
              {/* 页面标题 */}
              <div className="text-center mb-8">
                <h1 
                  className="text-5xl font-bold mb-4"
                  style={{ 
                    color: '#5a4229',
                    textShadow: '2px 2px 4px rgba(0,0,0,0.1)'
                  }}
                >
                  传统占卜
                </h1>
                <p 
                  className="text-xl"
                  style={{ color: '#6b5233' }}
                >
                  探索古老的东方智慧
                </p>
              </div>

              {/* 占卜类型选择 */}
              {!selectedType && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 w-full max-w-4xl">
                  {/* 八字排盘 */}
                  <Card 
                    variant="default" 
                    className="w-full cursor-pointer transition-all hover:shadow-2xl hover:scale-105 transform duration-300"
                    style={{ 
                      backgroundColor: '#f5ead6',
                      borderColor: '#a68b5b',
                      borderWidth: '3px',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                    }}
                    onClick={() => setSelectedType('bazi')}
                  >
                    <CardHeader className="text-center py-8">
                      <CardTitle 
                        className="text-4xl font-bold mb-4"
                        style={{ color: '#5a4229' }}
                      >
                        八字排盘
                      </CardTitle>
                      <p 
                        className="text-lg"
                        style={{ color: '#6b5233' }}
                      >
                        Four Pillars of Destiny
                      </p>
                    </CardHeader>
                    <CardContent className="text-center pb-8">
                      <p 
                        className="text-base leading-relaxed"
                        style={{ color: '#7d6347' }}
                      >
                        根据出生年月日时，排出天干地支，构成四柱八个字。通过分析这八个字的五行生克关系，可以推断一个人的性格、事业、财运、婚姻、健康等一生的命运趋势。
                      </p>
                    </CardContent>
                  </Card>

                  {/* 六爻占卜 */}
                  <Card 
                    variant="default" 
                    className="w-full cursor-pointer transition-all hover:shadow-2xl hover:scale-105 transform duration-300"
                    style={{ 
                      backgroundColor: '#f5ead6',
                      borderColor: '#a68b5b',
                      borderWidth: '3px',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                    }}
                    onClick={() => setSelectedType('liuyao')}
                  >
                    <CardHeader className="text-center py-8">
                      <CardTitle 
                        className="text-4xl font-bold mb-4"
                        style={{ color: '#5a4229' }}
                      >
                        六爻占卜
                      </CardTitle>
                      <p 
                        className="text-lg"
                        style={{ color: '#6b5233' }}
                      >
                        Liuyao Divination
                      </p>
                    </CardHeader>
                    <CardContent className="text-center pb-8">
                      <p 
                        className="text-base leading-relaxed"
                        style={{ color: '#7d6347' }}
                      >
                        通过三枚铜钱的抛掷，得到六个爻，组成一个卦象。占卜师根据卦象中的动爻、变爻以及与其他爻、日月的关系，来判断所问之事的发展过程、吉凶祸福。六爻对于具体问题的短期预测尤为擅长。
                      </p>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* 敬请期待界面 */}
              {selectedType && (
                <div className="w-full max-w-3xl space-y-6">
                  {/* 返回按钮 */}
                  <button
                    onClick={() => setSelectedType(null)}
                    className="px-6 py-3 rounded-lg transition-all hover:shadow-lg"
                    style={{
                      backgroundColor: '#f5ead6',
                      border: '2px solid #a68b5b',
                      color: '#5a4229',
                      fontWeight: 'bold'
                    }}
                  >
                    ← 返回选择
                  </button>

                  {/* 详情卡片 */}
                  <Card
                    variant="default"
                    className="w-full"
                    style={{
                      backgroundColor: '#f5ead6',
                      borderColor: '#a68b5b',
                      borderWidth: '3px',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.2)'
                    }}
                  >
                    <CardContent className="py-20 text-center">
                      <div className="mb-8">
                        <h2 
                          className="text-5xl font-bold mb-4"
                          style={{ color: '#5a4229' }}
                        >
                          {selectedType === 'bazi' ? '八字排盘' : '六爻占卜'}
                        </h2>
                        <p 
                          className="text-xl mb-8"
                          style={{ color: '#6b5233' }}
                        >
                          {selectedType === 'bazi' ? 'Four Pillars of Destiny' : 'Liuyao Divination'}
                        </p>
                      </div>
                      
                      <div 
                        className="text-3xl font-medium py-8 px-12 rounded-lg inline-block"
                        style={{ 
                          color: '#8b6f47',
                          backgroundColor: 'rgba(255,255,255,0.5)',
                          border: '2px dashed #a68b5b'
                        }}
                      >
                        敬请期待
                      </div>

                      <p 
                        className="mt-8 text-lg"
                        style={{ color: '#7d6347' }}
                      >
                        Coming Soon...
                      </p>
                    </CardContent>
                  </Card>

                  {/* 功能说明 */}
                  <Card
                    variant="default"
                    style={{
                      backgroundColor: 'rgba(245, 234, 214, 0.7)',
                      borderColor: '#a68b5b',
                      borderWidth: '2px'
                    }}
                  >
                    <CardContent className="py-6">
                      <h3 
                        className="text-xl font-bold mb-4"
                        style={{ color: '#5a4229' }}
                      >
                        即将上线的功能：
                      </h3>
                      <ul 
                        className="space-y-2 text-base"
                        style={{ color: '#6b5233' }}
                      >
                        {selectedType === 'bazi' ? (
                          <>
                            <li>• 精准的八字排盘计算</li>
                            <li>• 五行旺衰分析</li>
                            <li>• 十神关系解读</li>
                            <li>• 大运流年推演</li>
                            <li>• 性格特征分析</li>
                          </>
                        ) : (
                          <>
                            <li>• 智能起卦系统</li>
                            <li>• 六十四卦详解</li>
                            <li>• 动爻变卦分析</li>
                            <li>• 卦象吉凶判断</li>
                            <li>• 事态发展预测</li>
                          </>
                        )}
                      </ul>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          </Container>
        </div>
      </Sidebar>
    </ProtectedRoute>
  )
}

